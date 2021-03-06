import csv
import os
from copy import deepcopy

import galsim

from . import models
from .. import defaults


def _get_omit_fit(id_params, omit):
    omit_fit = {}

    for gal_id in id_params:
        params_omit = omit.get(gal_id, [])
        params = id_params[gal_id]
        galaxy_model = params['galaxy_model']
        cls = models.get_model_cls(galaxy_model)
        obj = cls(params_omit=params_omit)
        omit_fit[gal_id] = obj.omit_fit

    return omit_fit


def get_galaxy_model(params):
    """Return the image of a single galaxy optionally drawn with a psf.

    Look at :mod:`analysis.models` to figure out which galaxy models and psf
    models are supported as well as their corresponding implemented
    parameters. You can customize these files add your own galaxies if desired.

    Args:
        params(dict): Dictionary containing the information of a single
        galaxy where the keys is the name(str) of the parameter and the
        values are the values of the parameters.

    Returns:
        A :class:`galsim.GSObject`

    """

    galaxy_model = params['galaxy_model']
    gal_cls = models.get_model_cls(galaxy_model)
    gal_model = gal_cls(params)

    final = gal_model.gal

    if params.get('psf_flux', 0) != 0:

        if params.get('psf_flux', 1) != 1:
            raise ValueError('I do not think you want a psf of flux not 1')

        psf_cls = models.get_model_cls(params['psf_model'])
        psf_model = psf_cls(params)

        final = galsim.Convolve([final, psf_model.psf])

    return final


def get_galaxies_models(fit_params=None, id_params=None, g_parameters=None, **kwargs):
    """Return the model of a set of galaxies.

    One of the the following must be specified:
        fit_params (and nfit_params as **kwargs. Used specially in :mod:`runfits.py`).
        id_params
        g_parameters (from which id_params is extracted.)
    This function generates each of the galaxies specified in id_params and then
    sums them together to get a final galaxy.

    Args:
        fit_params(dict): Partial form of id_params that only includes the
                          parameters to be used for the fit.
                          For details, :class:`GParameters`
        id_params(dict): Dictionary containing each of the galaxies
                         parameters. For details, :class:`GParameters`
        g_parameters(:class:`GParameters`): An object containing different
                                            forms of the galaxy parameters.

    Returns:
        A :class:`galsim.GSObject`

    """
    # ToDo: Check if we need to convolve first and then add?
    if id_params is None and g_parameters is None:
        fit_params.update(kwargs)
        id_params = GParameters.convert_params_id(fit_params)

    if g_parameters is not None:
        id_params = g_parameters.id_params

    gals = []

    for gal_id in id_params:
        gals.append(get_galaxy_model(id_params[gal_id]))

    return galsim.Add(gals)


class GParameters(object):
    """Class that manages galaxies parameters obtained from galaxies.csv

    This class reads a galaxies.csv file located in the specified project
    directory and extracts the parameters of each galaxy contained in it.

        Args:
            project(str): String point to the directory specified by the user.
            id_params(dict): See Attributes for details. Makes it possible to
            create a :class:`GParameters` object without
            galaxies.csv file.

        Attributes:
            omit_fit(dict): Dictionary defined in containing
                the parameters that should not be included in the
                analysis for a particular galaxy model but could be
                necessary for drawing the galaxy.
            id_params(dict): Dictionary whose keys are the ids of each of the
                galaxies specified in galaxies.csv, and that map
                to another dictionary that can be taken in by
                :func:`get_galaxy_model`
            params(dict): Dictionary that encodes the same information as
                id_params but in a different form. Combines each of
                the dictionaries contained in id_params into a
                single dictionary that contains all parameters but
                in the form param_#.
            fit_params(dict): Dictionary similar to the params attribute but
                without the parameters specified in omit_fit.
            nfit_params(dict): Dictionary that contains all the parameters not
                contained in fit_params. Usually used for kwargs in conjunction with fit_params to
                draw Galaxies.
            ordered_fit_names(list): A list containing the keys of fit_params
                in a desirable order.
            num_galaxies(int): Number of galaxies specified.

    """

    def __init__(self, project=None, id_params=None, omit=None):
        if omit is None:
            omit = {}
        if project:
            if not os.path.isdir(project):
                raise OSError('Directory given does not exist.')

            filename = os.path.join(project, defaults.GALAXY_FILE)
            if not os.path.isfile(filename):
                raise OSError('The given file name is not in the directory:')

            # extract params from each of the rows in the given csvfile.
            # also remove empty params.
            with open(filename, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                id_params = {}
                for row in reader:
                    row_to_store = deepcopy(row)
                    gal_id = row['id']
                    for param in row:
                        if not row[param]:
                            row_to_store.pop(param)
                    row_to_store.pop('id')  # avoid redundancy
                    id_params[gal_id] = row_to_store

            # convert all appropriate values to floats,
            for gal_id in id_params:
                for key, value in id_params[gal_id].items():
                    try:
                        id_params[gal_id][key] = float(value)
                    except ValueError:
                        pass

        self.id_params = id_params
        self.params = GParameters.convert_id_params(self.id_params)
        self.omit_fit = _get_omit_fit(id_params, omit)
        self.fit_params = GParameters.convert_id_params(self.id_params,
                                                        self.omit_fit)
        self.nfit_params = self.get_nfit_params()
        self.ordered_fit_names = self.sort_model_param_names()
        self.num_galaxies = len(list(self.id_params.keys()))

    def get_nfit_params(self):
        """Extract :attr:`nfit_params` from :attr:`params` by noticing which
        parameters are in fit_params.
        """
        nfit_params = dict()
        for param in self.params:
            if param not in self.fit_params:
                nfit_params[param] = self.params[param]
        return nfit_params

    def sort_model_param_names(self):
        """Return the keys of :attr:`params` in an ordered specified by
        the class parameters. And when having more than one galaxy, all the
        parameters from one of the galaxies are ordered together.
        """
        param_names = []
        for gal_id in self.id_params:
            galaxy_model = self.id_params[gal_id]['galaxy_model']
            cls = models.get_model_cls(galaxy_model)
            for name in cls.parameters:
                for param in self.id_params[gal_id]:
                    if param not in self.omit_fit.get(gal_id, []):
                        if param == name:
                            param_names.append(param + '_' + str(gal_id))
        return param_names

    @staticmethod
    def convert_id_params(id_params, omit_fit={}):
        """Converts id_params to the format of :attr:`params`.

            Args:
                id_params(dict): Same as :attr:`id_params`
                omit_fit(dict): Dictionary that has the same purpose as
                                :attr:`omit_fit`

            Returns:
                A dictionary of params (dict).
        """
        params = {}
        for gal_id in id_params:
            for param in id_params[gal_id]:
                if param not in omit_fit.get(gal_id, []):
                    params[param + '_' + str(gal_id)] = (
                        id_params[gal_id][param])
        return params

    @staticmethod
    def convert_params_id(params):
        """Convert a dictionary params in the format of :attr:`params` to a
        dictionary in the format :attr:`id_params`
        """
        id_params = {}
        ids = []
        for param in params.keys():
            if param[-1] not in ids:
                ids.append(param[-1])  # appends last character of param

        for gal_id in ids:
            ID_params = {}
            for param in params.keys():
                if param[-1] == gal_id:
                    # slice last 2 characters to avoid '_1'
                    ID_params[param[:-2]] = params[param]
            id_params[gal_id] = ID_params

        return id_params
