"""Result accounting tests use synthetic files, never real-model training."""
import json
import pytest
from src.training.pilot_results import read_arm, compare_generations


def dump(path,value): path.write_text(json.dumps(value),encoding='utf-8')


@pytest.fixture
def artifacts(tmp_path):
    generation={'records':6,'samples':[{'id':str(i)} for i in range(6)],'semantic_style_scores':None,
        'form_compliance':.5,'imagery_micro_precision':.5,'imagery_micro_recall':.5,'imagery_micro_F1':.5,'density_accuracy':.5}
    history=[]
    for step in range(101):
        row={'step':step}
        if step:
            row.update(train_loss=1.,learning_rate=.0002,step_sources={'gold':8},source_exposures={'gold':8*step},
                id_exposures={'g':8*step},train_step_seconds=2.,processed_tokens=80*step)
        if step%10==0:
            row.update(eval_loss=2.,eval_token_accuracy=.3)
            dump(tmp_path/f'evaluation_{step:04d}.json',{'eval_loss':2.,'eval_token_accuracy':.3,'generation':generation})
        history.append(row)
    (tmp_path/'history.jsonl').write_text('\n'.join(json.dumps(r) for r in history),encoding='utf-8')
    dump(tmp_path/'config.json',{'training':{'learning_rate':.0002}})
    dump(tmp_path/'completion.json',{'optimizer_steps':100,'source_exposures':{'gold':800}})
    dump(tmp_path/'data_manifest.json',{'examples':[{'id':'g','source':'gold'}]})
    dump(tmp_path/'sampling_plan.json',[['g']*8 for _ in range(100)])
    return tmp_path, {'success':True,'peak_allocated_bytes':2**30,'wall_clock_seconds':250.}


def test_read_complete_arm(artifacts):
    result=read_arm(*artifacts)
    assert result['metrics']['training_seconds']==200
    assert result['metrics']['peak_vram_gib']==1
    assert result['source_counts']=={'gold':800}
    assert result['source_ratios']=={'gold':1.}


@pytest.mark.parametrize('field,value',[('train_loss',float('nan')),('learning_rate',.1),('step_sources',{'gold':7}),('source_exposures',{'gold':9}),('id_exposures',{'g':799})])
def test_reject_corrupt_accounting(artifacts,field,value):
    path,runtime=artifacts
    rows=[json.loads(x) for x in (path/'history.jsonl').read_text().splitlines()]
    rows[-1][field]=value
    (path/'history.jsonl').write_text('\n'.join(json.dumps(r) for r in rows))
    with pytest.raises(ValueError):read_arm(path,runtime)


def test_reject_incomplete_run(artifacts):
    path,runtime=artifacts
    rows=(path/'history.jsonl').read_text().splitlines()
    (path/'history.jsonl').write_text('\n'.join(rows[:-1]))
    with pytest.raises(ValueError):read_arm(path,runtime)


def test_generation_comparison_preserves_text_and_rejects_changed_controls():
    gold={str(i):{'text':'山水','form':'qijue7','style':{'imagery':['landscape'],'density':'medium'}} for i in range(6)}
    samples=[{'id':str(i),'target':'山水','requested_style':gold[str(i)]['style'],'output':'原样输出',
        'metrics':{'form_compliance':False},'imagery_rule_prediction':[],'density_rule_prediction':None} for i in range(6)]
    a={'generation':{'samples':samples}}
    result=compare_generations(a,a,gold)
    assert result[0]['B0-A']['generation']=='原样输出'
    assert result[0]['B0-A']['imagery_missing']==['landscape']
    assert result[0]['B0-A']['imagery_F1']==0
    samples[0]['target']='改动'
    with pytest.raises(ValueError):compare_generations(a,a,gold)
