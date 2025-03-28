#!/usr/bin/env python

from __future__ import print_function

import fastjet as fj
import fjcontrib
import fjext

import tqdm
import argparse
import os

import pythia8
import pythiaext
import pythiafjext

from heppy.pythiautils import configuration as pyconf

from pyjetty.mputils import mputils

import ROOT
ROOT.gROOT.SetBatch(1)


def main():
	parser = argparse.ArgumentParser(description='pythia8 in python', prog=os.path.basename(__file__))
	pyconf.add_standard_pythia_args(parser)
	args = parser.parse_args()	

	mycfg = []
	pythia = pyconf.create_and_init_pythia_from_args(args, mycfg)

	max_eta_hadron=3
	jet_R0 = 0.4
	# jet_selector = fj.SelectorPtMin(100.0) & fj.SelectorPtMax(125.0) & fj.SelectorAbsEtaMax(max_eta_hadron - 1.05 * jet_R0)
	jet_selector = fj.SelectorPtMin(10.0) & fj.SelectorAbsEtaMax(max_eta_hadron - 1.05 * jet_R0)
	parts_selector_h = fj.SelectorAbsEtaMax(max_eta_hadron)

	fj.ClusterSequence.print_banner()
	jet_def = fj.JetDefinition(fj.antikt_algorithm, jet_R0)

	qweights = [0.05, 0.1, 0.2, 0.3]
	qweights.insert(0, 0)

	rout = ROOT.TFile('gen_quench_out.root', 'recreate')
	hpt = []
	thf = []
	for i, w in enumerate(qweights):
		hname = 'hpt_{}'.format(i)
		htitle = 'hpt w={}'.format(w)
		rout.cd()
		h = ROOT.TH1F(hname, htitle, 10, mputils.logbins(10, 500, 10))
		hpt.append(h)
		if w <= 0:
			w = 1e-3
		hname = 'th_{}'.format(i)
		htitle = 'thf w={}'.format(w)
		rout.cd()
		th = ROOT.TF1(hname, 'gaus', -5 * w , 5 * w)
		th.SetParameter(0, 1)
		th.SetParameter(1, 0)
		th.SetParameter(2, w)
		thf.append(th)

	pbar = tqdm.tqdm(range(args.nev))
	for i in pbar:
		if not pythia.next():
			pbar.update(-1)
			continue

		parts_pythia_h = pythiafjext.vectorize_select(pythia, [pythiafjext.kFinal], 0, False)
		parts_pythia_h_selected = parts_selector_h(parts_pythia_h)

		jets_hv = fj.sorted_by_pt(jet_selector(jet_def(parts_pythia_h_selected)))
		if len(jets_hv) < 1:
			continue

		jets_h = None
		# do your things with jets here...
		for i, w in enumerate(qweights):
			if w > 0:
				_pthermal = []
				for p in parts_pythia_h_selected:
					_pth0 = fj.PseudoJet()
					_pth0.reset_PtYPhiM(p.perp() * (1.-w), p.rap(), p.phi(), p.m())
					_pthermal.append(_pth0)
					_pth1 = fj.PseudoJet()
					_pth1.reset_PtYPhiM(p.perp() * (0.+w), p.rap() + thf[i].GetRandom(-3 * w , 3 * w), p.phi() + thf[i].GetRandom(-3 * w , 3 * w), p.m())
					_pthermal.append(_pth1)
				jets_h = fj.sorted_by_pt(jet_selector(jet_def(_pthermal)))
			else:
				jets_h = jets_hv

			for j in jets_h:
				hpt[i].Fill(j.perp())

	rout.cd()
	for _f in thf:
		_f.Write()
	rout.Write()
	rout.Close()

	pythia.stat()
	pythia.settings.writeFile(args.py_cmnd_out)


if __name__ == '__main__':
	main()
