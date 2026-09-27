#!/usr/bin/env python3
"""Controlled eval setup and leakage prevention; no real model invocations."""
import copy
import tempfile
import unittest
from pathlib import Path
from eval_protocol import prepare_eval, neutral_preamble, validate_observations, blind_deliverables, prepare_blind
from runtime_protocol import load, ProtocolError
from workflow import ROOT, load_registry
from blind_eval import _select


class EvalProtocolTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve(); self.fixture=self.root/'fixture'; self.fixture.mkdir()
        (self.fixture/'brief.md').write_text('User needs export; accepted existing authority.\n')
        self.spec={'comparison':'skill','treatment':'with_without','scope':'role_task','role':'pm','stage':'define','task':'spec','skill':'prd-gwt',
                   'case':{'id':'export','prompt':'Write an observable export specification.','fixture_root':str(self.fixture),'inputs':['brief.md'],
                           'deliverables':['spec.md'],'rubric':[{'id':'behavior','criterion':'observable permission behavior','weight':1}]},
                   'model':'test-model','settings':{'temperature':0},'tools':['Read','Write'],
                   'budget':{'calls':6,'seconds':300,'output_tokens':4000},'plugin_new':str(ROOT),'contract_version':1,'seed':7}
    def prepare(self): return load(prepare_eval(self.spec,self.root/'run')['manifest'])
    def test_neutral_sources_have_no_loading_directives_for_any_role(self):
        r=load_registry()
        for role in r['roles']:
            t=next(t for t in r['tasks'] if t['role']==role)
            text=neutral_preamble(role,t,['Read','Write'])
            for marker in ('primary_skill','SKILL.md','lane_file','Orient','sdlc-workflow:', 'invoke','companion'):
                self.assertNotIn(marker,text)
    def test_isolated_arms_start_with_identical_inputs(self):
        m=self.prepare(); a,b=m['arms']['without'],m['arms']['with']
        self.assertEqual(a['input_sha256'],b['input_sha256']); self.assertIsNone(a['method_root'])
        (Path(a['project'])/'brief.md').write_text('changed arm A')
        self.assertNotEqual((Path(a['project'])/'brief.md').read_text(),(Path(b['project'])/'brief.md').read_text())
        self.assertEqual(m['quality_acceptance'],'pending'); self.assertEqual(m['actual_calls'],0)
    def test_old_new_requires_real_distinct_old_snapshot(self):
        self.spec['treatment']='old_new'
        with self.assertRaisesRegex(ProtocolError,'frozen'): self.prepare()
        self.spec['plugin_old']=str(ROOT)
        with self.assertRaisesRegex(ProtocolError,'distinct'): self.prepare()
    def test_missing_trace_or_unequal_tools_invalidates_comparison(self):
        m=self.prepare(); self.assertFalse(validate_observations(m,{})['valid'])
        obs={a:{'model':'test-model','settings':{'temperature':0},'tools':['Read'],'calls':1,'reads':[],
                'method_loads':[],'complete_trace':False} for a in m['arms']}
        result=validate_observations(m,obs)
        self.assertFalse(result['valid']); self.assertTrue(any('tools' in x for x in result['errors']))
    def test_control_reading_method_is_invalid(self):
        m=self.prepare()
        obs={a:{'model':'test-model','settings':{'temperature':0},'tools':['Read','Write'],'calls':1,'reads':[],
                'method_loads':[],'complete_trace':True} for a in m['arms']}
        obs['without']['reads']=[str(ROOT/'skills/prd-gwt/SKILL.md')]
        self.assertFalse(validate_observations(m,obs)['valid'])
    def test_judge_receives_only_deliverables(self):
        m=self.prepare()
        for arm in m['arms'].values():
            root=Path(arm['outputs']); (root/'spec.md').write_text('FR-1: observable behavior')
            (root/'2026-09-26-test-result.json').write_text('{"arm":"with"}')
        sides=blind_deliverables(m,self.root/'blind')
        self.assertEqual(set(sides),{'A','B'})
        self.assertEqual({p.name for p in (self.root/'blind/A').iterdir()},{'spec.md'})
    def test_legacy_blind_path_also_excludes_run_metadata(self):
        out=self.root/'outputs'; out.mkdir(); (out/'spec.md').write_text('ok')
        (out/'2026-09-26-x-manifest.json').write_text('secret arm')
        (out/'runs').mkdir(); (out/'runs/log.txt').write_text('method used')
        self.assertEqual(_select(str(out),None,[]),[('spec.md','spec.md')])
    def test_chain_requires_actual_handoffs(self):
        self.spec['comparison']='chain'
        with self.assertRaisesRegex(ProtocolError,'two concrete'): self.prepare()
    def test_chain_control_keeps_identical_downstream_method(self):
        self.spec['comparison']='chain'
        self.spec['steps']=[{'role':'pm','stage':'define','task':'spec','consumes':['brief.md'],'produces':['spec.md']},
                            {'role':'qa','stage':'define','task':'test-plan','consumes':['spec.md'],'produces':['test-plan.md']}]
        m=self.prepare(); a,b=m['arms']['without'],m['arms']['with']
        rel='step-2/skills/coverage-matrix/SKILL.md'
        self.assertEqual((Path(a['method_root'])/rel).read_bytes(),(Path(b['method_root'])/rel).read_bytes())
        self.assertFalse((Path(a['method_root'])/'step-1').exists())
    def test_controlled_blind_has_swapped_positions_and_validated_trace(self):
        from runtime_protocol import write_json
        output=prepare_eval(self.spec,self.root/'run'); m=load(output['manifest'])
        obs={a:{'model':'test-model','settings':{'temperature':0},'tools':['Read','Write'],'calls':1,'reads':[],
                'method_loads':[],'complete_trace':True} for a in m['arms']}
        for name,arm in m['arms'].items(): (Path(arm['outputs'])/'spec.md').write_text(name+' observable export behavior')
        observation=self.root/'observations.json'; write_json(observation,obs)
        result=prepare_blind(output['manifest'],observation)
        private=load(result['private_map'])
        self.assertEqual(private['mapping']['blind']['A'],private['mapping']['blind-swap']['B'])
        self.assertTrue((self.root/'run/blind/rubric.json').is_file())
        self.assertEqual({p.name for p in (self.root/'run/blind/A').iterdir()},{'spec.md'})


if __name__=='__main__': unittest.main()
