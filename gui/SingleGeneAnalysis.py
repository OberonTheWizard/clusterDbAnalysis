#!/usr/bin/env python

import easygui

import operator
import os
import sqlite3
import sys
import tempfile

from ClusterFuncs import *
from FileLocator import *

# The user probably doesn't want to see another box if they cancelled it themselves.
class UserCancelError(Exception):
    pass

# This is the base class for GUI errors displaying error messages.
# You can inherit from this class if you want to give a more descriptive name to your errors.
class GuiError(Exception):
    def __init__(self, errormsg):
        msg = "The program encountered the following error:\n\n%s\n\nPress OK to terminate the program.\n" %(errormsg)
        easygui.msgbox(msg=msg)

class NoGeneError(GuiError):
    pass

class ITEPGui:
    # Analyses
    def _get_nucleotide_fasta(self):
        geneinfo = self.accumulated_data['geneinfo']
        text = '>%s %s\n%s\n' %(geneinfo[0], geneinfo[9], geneinfo[10])
        easygui.textbox(text=text)
        return True
    def _get_amino_acid_fasta(self):
        geneinfo = self.accumulated_data['geneinfo']
        text = '>%s %s\n%s\n' %(geneinfo[0], geneinfo[9], geneinfo[11])
        easygui.textbox(text=text)
        return True
    # Analysis Related to getting related genes
    def _get_cluster_fasta(self, amino=True):
        r2c = self.accumulated_data['run_to_cluster']
        runid = self.accumulated_data['runid']
        clusterid = r2c[runid]
        genelist = getGenesInCluster(runid, clusterid, self.sqlite_cursor)
        geneinfo = getGeneInfo(genelist, self.sqlite_cursor)
        if amino:
            idx = 11
        else:
            idx = 10
        text = ''
        for gi in geneinfo:
            text += '>%s %s\n%s\n'%(gi[0], gi[9], gi[idx])
        easygui.textbox(text=text)
        return True

    def _get_presence_absence_table(self):
        pa_tbl_file = tempfile.NamedTemporaryFile(delete=False)
        pa_tbl_file_name = pa_tbl_file.name
        cluster = self.accumulated_data['run_to_cluster'][self.accumulated_data['runid']]
        os.system('db_getPresenceAbsenceTable.py -r %s -c %s > %s' %(self.accumulated_data['runid'], cluster, pa_tbl_file_name))
        text = ''.join( [ line for line in pa_tbl_file ] )
        easygui.textbox(text=text)
        return True

    def _make_crude_alignment(self):
        raise GuiError('This feature is not yet implemented in GUI form.')
    def _make_crude_tree(self):
        raise GuiError('This feature is not yet implemented in GUI form.')
    def _display_crude_tree(self):
        raise GuiError('This feature is not yet implemented in GUI form.')

    def _handle_cluster_run_options(self):
        valid_choices = [ 'Make Amino acid FASTA file', 'Make nucleotide FASTA file', 'Make a crude AA alignment', 
                          'Make a crude Newick tree from AA alignment', 'Display a crude Newick tree from AA alignment',
                          'Get a presence and absence table' ]
        option = easygui.choicebox("What do you want to do with it?", "Choose an analysis", valid_choices)        
        if option is None:
            return False
        if option == 'Make Amino acid FASTA file':
            self._get_cluster_fasta(amino=True)
        elif option == 'Make nucleotide FASTA file':
            self._get_cluster_fasta(amino=False)
        elif option == 'Make a crude AA alignment':
            self._make_crude_alignment()
        elif option == 'Make a crude Newick tree from AA alignment':
            self._make_crude_tree()
        elif option == 'Display a crude Newick tree from AA alignment':
            self._display_crude_tree()
        elif option == 'Get a presence and absence table':
            self._get_presence_absence_table()
        return True

    def _get_related_genes(self):
        # Entry into analyses for related genes.
        msg = ''' 
Please choose one of the following sets of settings to use for the analysis.

OrthoMCL runs are useful for identifying orthologs (genes likely to share a function)

maxbit runs are useful for identifying broader
gene families. c_xxx in the following list means xxx was used as a cutoff. Higher 
cutoffs mean more stringent similarity to define a family of related genes.

Note that only the options that contain your gene are listed here.
'''
        valid_choices = self.accumulated_data['run_to_cluster'].keys()

        if len(valid_choices) == 0:
            easygui.msgbox('The chosen gene is not found in any clustering results!')
            return True

        runid = easygui.choicebox(msg, 'Select a cluster run', valid_choices)

        # Canceling from here - just go back to the other menu
        if runid is None:
            return

        self.accumulated_data['runid'] = runid

        ok = True
        while ok:
            ok = self._handle_cluster_run_options()

        return True

    # Setup
    def _setUpClusterInfo(self):
        clusterrun_list = getClustersContainingGenes( [ self.accumulated_data['ITEP_id'] ], self.sqlite_cursor)
        run_to_cluster = {}
        for cr in clusterrun_list:
            run_to_cluster[cr[0]] = cr[1]
        self.accumulated_data['run_to_cluster'] = run_to_cluster
    def _setUpGeneInfo(self, alias):
        alias_file = locateAliasesFile()
        alias2gene = {}
        for line in open(locateAliasesFile()):
            spl = line.strip("\r\n").split("\t")
            alias2gene[spl[1]] = spl[0]
        if alias not in alias2gene:
            raise NoGeneError("Sorry, we could not find locus tag %s in our aliases file. It might not be in this database.\n" %(alias))

        itep_id = alias2gene[alias]
        geneinfo = getGeneInfo( [ itep_id ], self.sqlite_cursor)
        geneinfo = geneinfo[0]
        self.accumulated_data['alias'] = alias
        self.accumulated_data['alias_file'] = alias_file
        self.accumulated_data['ITEP_id'] = itep_id
        self.accumulated_data['geneinfo'] = geneinfo        
        return True
    def __init__(self, cur):
        self.valid_choices = [ 'Nucleotide FASTA', 'Amino acid FASTA', 'Related genes in other organisms']
        self.sqlite_cursor = cur
        self.accumulated_data = {}
        return
    # Interface
    def getLocusTag(self):
        gene_alias = easygui.enterbox("Please enter the locus tag of the gene you wish to study.")
        if gene_alias is None:
            raise UserCancelError('User cancelled the operation.')
        self._setUpGeneInfo(gene_alias)
        self._setUpClusterInfo()
        return gene_alias
    def askForChoice(self):
        # Display some information about the gene.
        geneinfo = self.accumulated_data['geneinfo']
        alias = self.accumulated_data['alias']
        msg = '''
You selected %s. Here is some basic information about this gene.

ITEP gene ID: %s
Organism: %s
Organism ID: %s
Contig ID: %s
Start location: %s
Stop location: %s
Strand: %s
Annotated Function: %s

What do you want to know about this gene?
''' %(alias, geneinfo[0], geneinfo[1], geneinfo[2], geneinfo[4], geneinfo[5], geneinfo[6], geneinfo[7], geneinfo[9])
    
        choice = easygui.choicebox(msg, 'Select an analysis.', gui.valid_choices)
    
        if choice is None:
            raise UserCancelError('User clicked CANCEL. No action taken.')
        return choice
    def runChosenAnalysis(self, choice):
        if choice == 'Nucleotide FASTA':
            self._get_nucleotide_fasta()
        elif choice == 'Amino acid FASTA':
            self._get_amino_acid_fasta()
        elif choice == 'Related genes in other organisms':
            self._get_related_genes()
        return True


if __name__ == "__main__":
    print "WARNING! This is highly experimental and will probably break in strange and wonderful ways."

    # Initialization
    con = sqlite3.connect(locateDatabase())
    cur = con.cursor()
    gui = ITEPGui(cur)

    # Lets get a focus gene to study.
    gene_alias = gui.getLocusTag()

    # What do you want to do with it?
    while 1:
        choice = gui.askForChoice()
        gui.runChosenAnalysis(choice)

    con.close()