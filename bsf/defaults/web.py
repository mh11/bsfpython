"""bsf.defaults.web

A package to centralise web configuration information.
"""

#
# Copyright 2013 - 2016 Michael K. Schuster
#
# Biomedical Sequencing Facility (BSF), part of the genomics core facility
# of the Research Center for Molecular Medicine (CeMM) of the
# Austrian Academy of Sciences and the Medical University of Vienna (MUW).
#
#
# This file is part of BSF Python.
#
# BSF Python is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BSF Python is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with BSF Python.  If not, see <http://www.gnu.org/licenses/>.


# Christoph Bock's ChIP-Seq default track colours.
# All ChIP-Seq factors are indexed in upper case.

chipseq_colours = \
    {
        "OTHER": "0,200,100",
        "HIGH": "57,39,140",
        "MEDIUM": "144,144,144",
        "LOW": "173,0,33",
        "H2": "102,51,204",
        # The following have been prefixed with H3,
        # a distinction needed for shallow peak calling.
        "H3K4ME1": "204,255,51",
        "H3K4ME2": "61,245,0",
        "H3K4ME3": "39,143,68",
        "H3K9ME1": "153,153,153",
        "H3K9ME2": "112,112,112",
        "H3K9ME3": "51,51,51",
        "H3K27ME1": "255,117,71",
        "H3K27ME2": "255,71,10",
        "H3K27ME3": "235,38,39",
        "H3K36ME1": "20,99,255",
        "H3K36ME2": "0,71,214",
        "H3K36ME3": "24,97,174",
        "H3K20ME1": "225,133,35",
        "H3K20ME2": "175,102,24",
        "H3K20ME3": "141,25,28",
        #
        "H4": "204,153,255",
        "AC": "153,0,77",
        #
        "H3K27AC": "153,0,77",
        "H3K56AC": "153,0,77",
        "H4K16AC": "153,0,77",
        #
        "K4ME1": "204,255,51",
        "K4ME2": "61,245,0",
        "K4ME3": "39,143,68",
        "K9ME1": "153,153,153",
        "K9ME2": "112,112,112",
        "K9ME3": "51,51,51",
        "K27ME1": "255,117,71",
        "K27ME2": "255,71,10",
        "K27ME3": "235,38,39",
        "K36ME1": "20,99,255",
        "K36ME2": "0,71,214",
        "K36ME3": "24,97,174",
        "K20ME1": "225,133,35",
        "K20ME2": "175,102,24",
        "K20ME3": "141,25,28",
        "CTCF": "204,153,0",
        "POL": "204,51,77",
        "EZH2": "0,128,153",
        "SUZ12": "128,204,51",
        "RING": "204,204,51",
        "P300": "204,0,0",
        "INPUT": "153,179,204",
        "WCE": "153,179,204"
    }

chipseq_default_factor = 'OTHER'
chipseq_default_colour = '0,0,0'


def get_chipseq_colour(factor=None):
    """Get the web colour for a ChIP-Seq factor.

    If the factor is not in the dictionary, the default colour for factor 'Other' will be returned.
    @param factor: ChIP-Seq factor (e.g. H3K36me3, H3K4me1, ...)
    @type factor: str
    @return: Comma-separated RGB value triplet
    @rtype: str
    """

    if not factor:
        return chipseq_colours[chipseq_default_factor]

    factor_upper = factor.upper()

    if factor_upper in chipseq_colours:
        return chipseq_colours[factor_upper]
    else:
        return chipseq_colours[chipseq_default_factor]