"""Protocol tests only: no pretrained model, CUDA training, or network."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json
import pytest
from src.training.frozen_pilot import read_json, read_rows, select_split, label_counts, assert_matched, audit_config, sampling_plan
from src.training.pilot_protocol import check_isolation, load_pilot_dataset
from src.training.pilot_evaluation import teacher_counts, score_generations, evaluate
from src.data.dataset import PoetryTrainingDataset
ROOT = Path(__file__).resolve().parents[1]
A = ROOT / 'configs/b0_pilot_gold_only.json'
B = ROOT / 'configs/b0_pilot_gold_partial_silver.json'


def test_frozen_split_reproducible_partition():
    split = read_json(ROOT / 'configs/b0_pilot_split.json')
    rows = read_rows(ROOT / split['gold_source'])
    train, evaluation = select_split(rows, 20260926)
    other = select_split(list(reversed(rows)), 20260926)
    assert (train, evaluation) == other
    assert [r['id'] for r in train] == split['train_ids']
    assert [r['id'] for r in evaluation] == split['eval_ids']
    assert len(train) == 18 and len(evaluation) == 6
    assert not set(split['train_ids']) & set(split['eval_ids'])
    assert label_counts(evaluation)['form:qijue7'] == label_counts(evaluation)['form:qilv7'] == 3
    assert set(label_counts(train)) == set(label_counts(rows))


def test_actual_frozen_inputs_and_provenance():
    for path in (A, B):
        config, split, audit = audit_config(path, ROOT)
        assert audit['prohibited_overlap'] == audit['id_overlap'] == 0
        ds = load_pilot_dataset(config, ROOT, training=True)
        assert len(ds) == config['data']['records']
        assert {ds[i].id for i in range(len(ds))}.isdisjoint(split['eval_ids'])
        assert all(ds[i].provenance['annotation'] and ds[i].supervision_type for i in range(len(ds)))


@pytest.mark.parametrize('section,key,value', [('training','max_optimizer_steps',101), ('training','learning_rate',.001),
    ('training','gradient_accumulation_steps',4), ('training','eval_every_steps',20), ('model','max_length',256), ('lora','r',8)])
def test_budget_mismatch_rejected(section, key, value):
    a, b = read_json(A), read_json(B); b[section][key] = value
    with pytest.raises(ValueError): assert_matched(a, b)


def test_exact_sampling_budget_no_epoch_tails():
    a, b = read_json(A), read_json(B); assert_matched(a, b)
    plans = []
    for config in (a, b):
        ds = load_pilot_dataset(config, ROOT, training=True)
        plan = sampling_plan(ds.sampling_weights, 100, 1, 8, 20260926)
        assert len(plan) == 100 and all(len(step) == 8 for step in plan)
        assert plan == sampling_plan(ds.sampling_weights, 100, 1, 8, 20260926)
        plans.append([ds[i].source for step in plan for i in step])
    assert plans[0].count('gold') == 800
    assert .25 < plans[1].count('gold') / 800 < .35


def test_evaluation_never_drops_controls():
    split = read_json(ROOT / 'configs/b0_pilot_split.json')
    ds = PoetryTrainingDataset(ROOT / split['eval_path'], schema_path=ROOT / 'configs/style_schema.json', training=False, control_dropout=1., seed=20260926)
    ds.set_epoch(100)
    assert all(len(ex.active_controls) == 7 and ex.active_controls == ex.available_controls for ex in ds)


@pytest.mark.parametrize('prohibited', ['evaluation', 'pending', 'high_risk', 'variant'])
def test_leakage_fails_closed(prohibited):
    train = [{'id':'train', 'text':'甲'}]; evaluation = [{'id':'eval', 'text':'乙'}]; pending = []; flags = []; variants = []
    if prohibited == 'evaluation': train.append(deepcopy(evaluation[0]))
    if prohibited == 'pending': pending = [{'id':'train'}]
    if prohibited == 'high_risk': flags = [{'id':'train', 'flags':[{'severity':'high'}]}]
    if prohibited == 'variant': variants = [{'members':['train','eval']}]
    with pytest.raises(ValueError): check_isolation(train, evaluation, pending, flags, variants)


def test_teacher_counts_masks_prompt_and_padding():
    import torch
    labels = torch.tensor([[-100,-100,2,3,-100]])
    logits = torch.zeros(1,5,4); logits[0,1,2] = 1; logits[0,2,1] = 1
    assert teacher_counts(logits, labels) == (1,2)


def test_invalid_generation_keeps_denominator():
    split = read_json(ROOT / 'configs/b0_pilot_split.json')
    examples = list(PoetryTrainingDataset(ROOT / split['eval_path'], schema_path=ROOT / 'configs/style_schema.json'))
    result = score_generations([''] * 6, examples, read_json(ROOT / 'configs/imagery_lexicon_v1.json'))
    assert result['records'] == 6 and result['form_compliance'] == result['imagery_micro_F1'] == result['density_accuracy'] == 0
    assert result['semantic_style_scores'] is None


def test_evaluation_weighted_targets_and_restores_training_rng():
    import torch
    from src.data.dataset import TrainingExample
    class Tokenizer:
        pad_token_id=0; eos_token_id=3
        def apply_chat_template(self, conversation, **kwargs):
            return [1,1] if len(conversation)==1 else [1,1] + [2]*len(conversation[1]['content']) + [3]
        def decode(self, ids, **kwargs): return ''
    class Model:
        training=True
        def train(self, value=True): self.training=value
        def eval(self): self.train(False)
        def __call__(self, **batch):
            assert not self.training
            torch.rand(1)  # Evaluation must not perturb future training dropout RNG.
            n = int((batch['labels'][:,1:] != -100).sum())
            return SimpleNamespace(loss=torch.tensor(float(n)), logits=torch.zeros(1,batch['labels'].shape[1],4))
        def generate(self, **kwargs): return torch.tensor([[1,1,3]])
    examples = [TrainingExample(str(n),'qijue7',{'imagery':['landscape'],'density':'medium'},'甲'*n,'prompt') for n in (1,3)]
    config = read_json(A); model = Model(); state = torch.get_rng_state().clone()
    result = evaluate(model, Tokenizer(), examples, config, read_json(ROOT / 'configs/imagery_lexicon_v1.json'), device='cpu')
    assert result['eval_loss'] == pytest.approx((2*2 + 4*4)/6)
    assert result['supervised_tokens'] == 6 and model.training
    assert torch.equal(state, torch.get_rng_state())
