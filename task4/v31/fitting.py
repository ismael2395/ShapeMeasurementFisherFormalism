#!/usr/bin/env python
"""Allows the user to do N fittings of a galaxy produced in generate.py given a SNR and compare with the fisher formalism by displaying biases and 
correlation coefficients,etc. and also by displaying a triangle plot that summarizes this results and displays data points."""

import argparse

import os

import defaults

import info
                   
import galfun

import fisher

def main():
    """Give the instructions to run a bunch of fits either here or in SLAC and to reproduce results and produce triangle plot."""

    parser = argparse.ArgumentParser(
        description = ('Displays a triangle plot comparing the expected noise'
                       'bias calculation with the fisher matrix formalism for'
                       'a given file of galaxies.'), 
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)


    parser.add_argument('-p', '--project', default=defaults.PROJECT, 
    metavar='PROJECT', 
    type=str,
    help=('Specify a directory name where the project will be saved. In this fashion each individual project represents one analysis.'))

    parser.add_argument('--snr', metavar = 'SNR', default = defaults.SNR, 
    type = int,
    help = ('Specify signal to noise ratio of the run. Should use same snr' 
            'between run_fits and produce_results, else it does not work.'))

    parser.add_argument('-n', '--number-fits', default = 1, 
    type = int,
    help = 'Specify how many fits are run.')

    parser.add_argument('-rf', '--run-fits', action = 'store_true',
    help = ('Run N different instantiations of noise of the added galaxies' 
            'to produce a triangle plot. Fits all galaxies in given file N'
            'times.'))

    parser.add_argument('-rfs', '--run-fits-slac', metavar = 'SLAC_COMPUTER',
    help = 'Same as above but have to be logged in a SLAC computer.')

    parser.add_argument('-pr', '--produce-results', action = 'store_true',
    help = ('Read each of the files produces from a fits trial in project' 
            'directory and creates a triangle plot comparing fisher to'
            'residuals.'))

    parser.add_argument('--verbose', action = 'store_true',
    help = ('Prints technical information about the galaxy and the defaults' 
            'used for the fitting'))

    parser.add_argument('--info-file', action = 'store_true',
    help = 'Write relevant information to a .txt file for future reference')

    args = parser.parse_args()

    if args.run_fits:
        for i in range(args.number_fits):
            os.system("python runfits.py " + str(i) + " " + str(args.snr) + 
                      " " +  str(args.project)) 
        #write snr to file, so no confusion as to what snr we have later.
        snr_file_name = os.path.join(args.project,defaults.SNR_FILE)
        with open(snr_file_name, 'w') as snrfile:
            snrfile.write(str(args.snr))

    elif args.run_fits_slac:
        os.system("bsub -q " + str(args.run_fits_slac) + " -J \"name[1-" + str(args.number_fits) + "]\" \"python runfits.py \$LSB_JOBINDEX " 
            + str(args.snr) + " " + str(args.project) + "\"")

        snr_file_name = os.path.join(args.project,defaults.SNR_FILE)
        with open(snr_file_name, 'w') as snrfile:
            snrfile.write(str(args.snr))

    elif args.produce_results:

        #get snr from file
        snr_file_name = os.path.join(args.project,defaults.SNR_FILE)
        with open(snr_file_name, 'r') as snrfile:
            snr = snrfile.readline()

        #count number of files we are producing results from. 
        rltsdir = os.path.join(args.project,defaults.RESULTS_DIR)
        number_fits = 0
        for filename in os.listdir(rltsdir):
            number_fits += 1


        os.system("python readfits.py " +  str(args.project) + " " +  str(snr)      + " " + str(number_fits))

        g_parameters = galfun.GParameters(args.project)
        fish = fisher.Fisher(g_parameters, snr)
        information = info.Info(g_parameters, fish, number_fits = number_fits)

        if args.verbose:
            information.printInfo()

        if args.info_file:
            information.writeInfo(args.project)



if __name__ == '__main__':
    main()