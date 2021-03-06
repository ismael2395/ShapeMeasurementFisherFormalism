"""Multipurpose module that contains important functions ranging from managing parameters of 
generated galaxies to extracting information from relevant files.
"""
import csv
import math

import numpy as np

from .. import defaults


def read_results(project_path, g_parameters, fish):
    orig_image = fish.image
    mins = defaults.get_minimums(g_parameters, orig_image)
    maxs = defaults.get_maximums(g_parameters, orig_image)

    residuals = {}
    pulls = {}
    redchis = []  # list containing values of reduced chi2 for each fit.
    results_dir = project_path.joinpath(defaults.RESULTS_DIR)

    # read results from results_dir's files.
    for fit_file in results_dir.iterdir():
        with open(fit_file) as csvfile:
            reader = csv.DictReader(csvfile)
            for i, row in enumerate(reader):
                redchis.append(float(row['redchi']))
                for param in g_parameters.fit_params:
                    if param not in residuals:
                        residuals[param] = []
                    if param not in pulls:
                        pulls[param] = []
                    residual = (float(row[param]) -
                                float(g_parameters.params[param]))

                    pull = (residual /
                            math.sqrt(fish.covariance_matrix[param, param]))

                    residuals[param].append(residual)
                    pulls[param].append(pull)

    biases = {param: np.mean(residuals[param]) for param in residuals}
    pull_means = {param: np.mean(pulls[param]) for param in residuals}
    res_stds = {param: np.std(residuals[param]) for param in residuals}
    pull_mins = {param: ((mins[param] - float(g_parameters.params[param])) /
                         math.sqrt(fish.covariance_matrix[param, param])) for
                 param in residuals}
    pull_maxs = {param: ((maxs[param] - float(g_parameters.params[param])) /
                         math.sqrt(fish.covariance_matrix[param, param])) for
                 param in residuals}

    return pulls, residuals, biases, pull_means, res_stds, pull_mins, pull_maxs, redchis
