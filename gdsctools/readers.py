"""IO functionalities"""
import pandas as pd
import pylab
import numpy as np
import easydev


__all__ = ['IC50', 'GenomicFeatures', 'CosmicRows', 'Reader']


class Reader(object):
    """Base class to read csv file"""
    def __init__(self, filename, sep="\t"):
        """.. rubric:: Constructor

        :param input: could be a filename

        """
        self._filename = filename
        self._sep = sep

    def read_matrix_from_r(self, name):
        print("Reading matrix %s " % (name))
        self.session.run("rnames = rownames(%s)" % name)
        self.session.run("cnames = colnames(%s)" % name)
        self.session.run("data = %s" % name)

        cnames = self.session.cnames
        rnames = self.session.rnames
        data = self.session.data
        df = pd.DataFrame(data=data.copy())
        df.columns = [x.strip() for x in cnames]
        df.index = [x.strip() for x in rnames]
        return df

    def __str__(self):
        self.df.info()
        return ""

    def to_csv(self, filename, sep=None):
        """Save data into a CSV file (actually, TSV) """
        if sep is None:
            sep = self._sep
        self.df.to_csv(filename, sep=sep)


class CosmicRows(object):
    """Parent class to IC50 and GenomicFeatures to handle cosmic identifiers"""
    def _get_cosmic(self):
        return list(self.df.index)
    cosmicIds = property(_get_cosmic,
            doc="return list of cosmic ids (could have duplicates)")


class IC50(Reader, CosmicRows):
    """Reader of IC50 data set

    The input matrix must be a tab-separated value file (TSV) although
    comma-seprated files may be provided (see constructor section here below).

    The matrix must have at least 2 columns and 2 rows.

    The first row is the header describing the columns' contents. One column
    must be named "COSMIC ID". Other columns must be named "Drug_XX_IC50"
    where XX is a positive integer (order is not important).

    The column "COSMIC ID" contains the cosmic identifiers (cell line). The
    other columns should be filled with the IC50s corresponding to a pair
    of COSMIC Id and Drug.

    Extra columns (e.g., tissue, sample name, MSI, features) will be ignored.

    Here is a simple example of a valid TSV file::

        COSMIC ID   Drug_1_IC50 Drug_20_IC50
        111111      0.5         0.8
        222222      1           2


    A test file is provided in the gdsctools package::

        from gdsctools import ic50_test

    You can read it using this class and plot information as follows:

    .. plot::
        :width: 80%
        :include-source:

        from gdsctools import IC50, ic50_test
        r = IC50(ic50_test)
        r.plot_ic50_count()

    You can get basic information using the print function::

        >>> from gdsctools import IC50, ic50_test
        >>> r = IC50(ic50_test)
        >>> print(r)
        Number of drugs: 11
        Number of cell lines: 988
        Percentage of NA 0.206569746043


    """
    def __init__(self, filename='ANOVA_input.txt', sep="\t"):
        """.. rubric:: Constructor

        :param filename: input filename of IC50s. May also be an instance
            of :class:`IC50` or a valid dataframe. The data is stored as a
            dataframe in the attribute called :attr:`df`.
        :param sep: separator between columns (default to tabulation)


        """
        super(IC50, self).__init__(filename, sep=sep)

        if isinstance(filename, str):
            self.rawdf = pd.read_csv(self._filename, sep=self._sep)
            columns = ['COSMIC ID']
            columns += [x for x in self.rawdf.columns if x.startswith('Drug')]
            self.df = self.rawdf[columns].copy() # is copy  required ?
            self.df.set_index('COSMIC ID', inplace=True)
        elif isinstance(filename, IC50):
            self.df = filename.df.copy()
        elif isinstance(filename, pd.DataFrame):
            self.df = filename.copy()
        else:
            raise TypeError("Input must be a filename, a IC50 instance, or " +
                            "a dataframe.")

    def _get_drugs(self):
        return list(self.df.columns)
    drugIds = property(_get_drugs, doc='list the drug identifier name')

    def plot_ic50_count(self):
        """Plots the fraction of valid/measured IC50 per drug

        :return: the fraction of valid/measured IC50 per drug"""
        data = self.df.count()/len(self.df)
        pylab.clf()
        pylab.plot(data.values)
        pylab.grid()
        pylab.xlim([0, len(self.drugIds)+1])
        pylab.xlabel('Drug index')
        pylab.ylim([0,1])
        pylab.ylabel('Percentage of valid IC50')
        return  data

    def hist(self, bins=20, **kargs):
        """Histogram of the measured IC50

        :param bins: binning of the histogram
        :param **kargs: any argument accepted by pylab.hist function.
        :return: all measured IC50"""
        data = [x for x in self.df.values.flatten() if not np.isnan(x)]
        pylab.clf()
        pylab.hist(data, bins=bins, **kargs)
        pylab.grid()
        pylab.xlabel('log IC50')
        return data

    def __str__(self):
        txt = "Number of drugs: %s\n" % len(self.drugIds)
        txt += "Number of cell lines: %s\n" % len(self.df)
        N = len(self.drugIds) * len(self.df)
        Nna = self.df.isnull().sum().sum()
        txt += "Percentage of NA {0}\n".format(Nna / float(N))
        return txt


class GenomicFeatures(Reader, CosmicRows):
    """Read Matrix with Genomic Features

    There are compulsary column names required (note the spaces):

        - 'COSMIC ID'
        - 'Tissue Factor Value'
        - 'Sample Name'
        - 'MS-instability Factor Value'

    and features can be also encoded with the following convention:

        - columns ending in "_mut" to encode a gene mutation (e.g., BRAF_mut)
        - columns starting with "gain_cna"
        - columns starting with "loss_cna"

    Those columns will be removed:

        - starting with `Drug_`, which are supposibly from the IC50 matrix


    ::

        >>> from gdsctools import GenomicFeatures
        >>> gf = GenomicFeatures()
        >>> print(gf)
        Genomic features distribution
        Number of unique tissues 27
        Number of unique features 677 with
        - Mutation: 270
        - CNA (gain): 116
        - CNA (loss): 291

    """
    def __init__(self, filename=None, sep="\t"):
        """.. rubric:: Constructor

        If not file is provided, using the edfault file provided in the 
        package that is made of 1001 cell lines times 680 features.

        """
        # first reset the filename to the shared data (if not provided)
        if filename is None:
            filename = easydev.get_share_file('gdsctools', 'data',
                            'genomic_features.tsv')
        super(GenomicFeatures, self).__init__(filename)

        if isinstance(filename, str):
            self.df = pd.read_csv(self._filename, sep=self._sep)
            assert 'COSMIC ID' in self.df.columns, \
                "the features input file must contains a column named COSMIC ID"
            self.df.set_index('COSMIC ID', inplace=True)
        else:
            try:
                # there is a df attribute
                self.df = filename.df.copy()
            except:
                # it is a dataframe
                self.df = filename

        # Remove columns related to Drug, which should be in the IC50 matrix
        self.df = self.df[[x for x in self.df.columns
            if x.startswith('Drug_') is False]]

        # There are several types of features e.g., mutation, CNA,
        # methylation but all are stored within the same file
        # Besides, these 3 first columns are compulsary
        self._col_tissue = 'Tissue Factor Value'
        self._col_sample = 'Sample Name'
        self._col_msi = 'MS-instability Factor Value'

        names = [self._col_tissue, self._col_sample, self._col_msi]
        for name in names:
            assert name in self.df.columns , 'Could not find column %s' % name

    def _get_features(self):
        return list(self.df.columns)
    features = property(_get_features, doc="return list of features")

    def _get_tissues(self):
        return list(self.df[self._col_tissue])
    tissues = property(_get_tissues, doc='return list of tissues')
    
    def _get_unique_tissues(self):
        return list(self.df[self._col_tissue].unique())
    unique_tissues = property(_get_unique_tissues, doc='return set of tissues')

    def plot(self):
        """Histogram of the tissues found

        .. plot::
            :include-source:
            :width: 80%

            from gdsctools import GenomicFeatures
            gf = GenomicFeatures() # use the default file
            gf.plot()


        """
        data = pd.get_dummies(self.df['Tissue Factor Value']).sum()
        data.index = [x.replace("_", " ") for x in data.index]
        # deprecated but works for python 3.3
        try:
            data.sort_values(ascending=False)
        except:
            data.sort(ascending=False)
        pylab.figure(1)
        pylab.clf()
        labels = list(data.index)
        pylab.pie(data, labels=labels)
        pylab.figure(2)
        data.plot(kind='barh')
        pylab.grid()
        pylab.xlabel('Occurences')
        pylab.tight_layout()
        return data

    def __str__(self):
        txt = 'Genomic features distribution\n'
        Ntissue = len(self.df[self._col_tissue].unique())
        txt += 'Number of unique tissues {0}\n'.format(Ntissue)

        # -3 since we have also the MSI, tissue, sample columns
        Nfeatures = len(self.features)
        txt += 'Number of unique features {0} with\n'.format(Nfeatures-3)

        n_mutations = len([x for x in self.df.columns if x.endswith("_mut")])
        txt += "- Mutation: {}\n".format(n_mutations)

        n_gain = len([x for x in self.df.columns if x.startswith("gain_cna")])
        txt += "- CNA (gain): {}\n".format(n_gain)
        n_loss = len([x for x in self.df.columns if x.startswith("loss_cna")])
        txt += "- CNA (loss): {}".format(n_loss)
        return txt

    def drop_tissue_in(self, tissues):
        """Drop tissues from the list

        :param list tissues: a list of tissues to drop. If you have only
            one tissue, can be provided as a string. Since rows are removed
            some features (columns) may now be empty (all zeros). If so, those
            columns are dropped (except for the special columns (e.g, MSI).

        """
        tissues = easydev.to_list(tissues)
        mask = self.df[self._col_tissue].isin(tissues) == False
        self.df = self.df[mask]
        self._cleanup()

    def keep_tissue_in(self, tissues):
        """Drop tissues from the list

        :param list tissues: a list of tissues to drop. If you have only
            one tissue, can be provided as a string. Since rows are removed
            some features (columns) may now be empty (all zeros). If so, those
            columns are dropped (except for the special columns (e.g, MSI).

        """
        tissues = easydev.to_list(tissues)
        tissues = easydev.to_list(tissues)
        mask = self.df[self._col_tissue].isin(tissues)
        self.df = self.df[mask]
        self._cleanup()

    def _cleanup(self, required_features=0):
        to_ignore = [self._col_tissue, self._col_msi, self._col_sample]
        # create a view ignoring the informative columns
        view = self.df[[x for x in self.df.columns if x not in to_ignore]]

        todrop = list(view.columns[view.sum() <= required_features])
                
        self.df.drop(todrop, axis=1, inplace=True)


class PANCAN(Reader):
    """Reads RData file wit all genomic features including methylation.

    will be removed. Used to read original data in R format but
    will provide the data as CSV or TSV
    """
    def __init__(self, filename=None):
        if filename is None:
            filename = easydev.get_share_file('gdsctools', 'data',
                            'PANCAN_simple_MOBEM.rdata')
        super(PANCAN, self).__init__(filename)
        # Remove R dependencies
        from biokit.rtools import RSession
        self.session = RSession()
        self.session.run('load("%s")' %self._filename)
        self.df = self.read_matrix_from_r('MoBEM')


class Extra(Reader):
    def __init__(self, filename="djvIC50v17v002-nowWithRMSE.rdata"):
        super(Extra, self).__init__(filename)
        # Remove R dependencies
        from biokit.rtools import RSession
        self.session = RSession()
        self.session.run('load("%s")' %self._filename)

        # 3 identical matrices containing AUC, IC50 and
        self.dfAUCv17= self.read_matrix_from_r('dfAUCv17')
        self.dfIC50v17 = self.read_matrix_from_r('dfIC50v17')
        # Residual
        self.dfResv17 = self.read_matrix_from_r('dfResv17')

        # This df holds the xmid/scale parameters for each cell line
        # Can be visualised using the tools.Logistic class.
        self.dfCL= self.read_matrix_from_r('dfCL')

        # There is an extra matrix called MoBEM, which is the same as in the
        # file

    def hist_residuals(self, bins=100):
        """Plot residuals across all drugs and cell lines"""
        data = [x for x in self.dfResv17.fillna(0).values.flatten() if x != 0]
        pylab.clf()
        pylab.hist(data, bins=bins, normed=True)
        pylab.grid(True)
        pylab.xlabel('Residuals')
        pylab.ylabel(r'\#')

    def scatter(self):
        from biokit import scatter
        s = scatter.ScatterHist(self.dfCL)
        s.plot(kargs_histx={'color':'red', 'bins':20},
                kargs_scatter={'alpha':0.9, 's':100, 'c':'b'},
                kargs_histy={'color':'red', 'bins':20})

    def hist_ic50(self, bins=100):
        data = [x for x in self.dfIC50v17.fillna(0).values.flatten() if x != 0]
        pylab.clf()
        pylab.hist(data, bins=bins, normed=True)
        pylab.grid(True)
        pylab.xlabel('IC50')
        pylab.ylabel(r'\#')

    def hist_auc(self, bins=100):
        data = [x for x in self.dfAUCv17.fillna(0).values.flatten() if x != 0]
        pylab.clf()
        pylab.hist(data, bins=bins, normed=True)
        pylab.grid(True)
        pylab.xlabel('AUC')
        pylab.ylabel(r'\#')


