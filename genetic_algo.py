import numpy as np
import typing
import tqdm
import os

import alpha as alpha_lib

CONFIG = {
    'population': 100,
    'selection_count' : 50,
    'mutation_rate': 0.02,
    'iteration': 15
}

TEMPLATE = '''
    alpha=<group_op>(<data_tsz_op>(ts_backfill(<data_1>, <days_1>), <days_2>), <group_1>);
    alpha_gpm = group_mean(alpha, <weight>, <group_2>);
    resid = <compare_op>(alpha, alpha_gpm);
    <ts_decay_op>(group_neutralize(resid, <group_3>), <days_3>)
'''

SPACE = {
    '<data_1>': ['anl4_gric_high'],
    '<group_op>': ['group_zscore', 'group_neutralize', 'group_rank'],
    '<data_tsz_op>': ['ts_zscore', 'ts_rank', 'ts_delta', 'ts_av_diff'],
    '<days_1>': ['21', '63'],
    '<days_2>': ['10', '21', '42', '63', '126', '252'],
    '<group_1>': ['market', 'sector', 'industry', 'subindustry', 'country', 'exchange'],
    '<weight>': ['5', '10', 'cap', 'log(cap)', 'rank(cap)'],
    '<group_2>': ['market', 'sector', 'industry', 'subindustry', 'country', 'exchange'],
    '<compare_op>': ['vector_neut', 'subtract', 'divide', 'regression_neut'],
    '<group_op_2>' : ['group_neutralize', 'group_zscore', 'group_median', 'group_rank', 'group_scale'],
    '<group_3>': ['market', 'sector', 'industry', 'subindustry', 'country', 'exchange'],
    '<days_3>': ['5', '10', '21', '42', '63'],
    '<ts_decay_op>': ['ts_mean', 'ts_decay_linear'],
}

SETTINGS = {
    "instrumentType": "EQUITY",
    "region": "USA",
    "universe": "TOP3000",
    "delay": 1,
    "decay": 0,
    "neutralization": "INDUSTRY",
    "truncation": 0.1,
    "pasteurization": "ON",
    "unitHandling": "VERIFY",
    "nanHandling": "OFF",
    "language": "FASTEXPR",
    "visualization": False
}

class GeneticAlgo:
    def __init__(self, name: str, template: str, space: typing.Dict[str, typing.List[str]], settings: typing.Dict[str, str], config: typing.Dict=CONFIG):
        self.name = name
        self.template = template
        self.space = space
        self.settings = settings
        self.config = config

        self.gene_database: typing.Dict[str, typing.Dict[str, str]] = {}
        self.generation_database: typing.List[typing.Dict[str, alpha_lib.Alpha]] = []

    @staticmethod
    def generate_alpha_name(prefix: str, iteration: int, ind: int):
        return f'{prefix}_{iteration}_{ind}'

    def generate_initial_population(self):
        alphas: typing.Dict[str, alpha_lib.Alpha] = {}
        for i in range(self.config['population']):
            name = self.generate_alpha_name(self.name, 0, i)
            expr = self.template
            self.gene_database[name] = {}
            for gene_name, gene_vals in self.space.items():
                self.gene_database[name][gene_name] = np.random.choice(gene_vals)
                expr = expr.replace(gene_name, self.gene_database[name][gene_name])
            alphas[name] = alpha_lib.Alpha(
                name,
                payload={
                    "type": "REGULAR",
                    "settings": self.settings,
                    "regular": expr
                }
            )
            alphas[name].to_disk()
        finish_alphas = self.collect_alphas(alphas)
        self.generation_database.append(finish_alphas)
    
    @staticmethod
    def collect_alphas(alphas: typing.Dict[str, alpha_lib.Alpha])->typing.Dict[str, alpha_lib.Alpha]:
        uncollected_names = list(alphas.keys())
        ret_alphas = {}
        with tqdm.tqdm(len(uncollected_names)) as pbar:
            while len(uncollected_names) > 0:
                for name, alpha in alphas.items():
                    if name not in uncollected_names:
                        continue
                    if os.path.isfile(os.path.join(alpha_lib.AlphaStage.RESULT.value, alpha.filename)):
                        ret_alphas[name] = alpha_lib.Alpha.read_from_disk(os.path.join(alpha_lib.AlphaStage.RESULT.value, alpha.filename))
                        uncollected_names.remove(name)
                        pbar.update(1)
        return ret_alphas
    
    @staticmethod
    def selection(alphas: typing.Dict[str, alpha_lib.Alpha]) -> typing.Dict[str, alpha_lib.Alpha]:
        names = list(alphas.keys())
        fitnesses = [
            (alphas[name].result['is']['sharpe'] if alphas[name].result['is']['sharpe'] is not None else 1) *
            (alphas[name].result['is']['fitness'] if alphas[name].result['is']['fitness'] is not None else 1)
            for name in names
        ]
        threshold = np.median(fitnesses)
        return {
            k: v for k, v in alphas.items() if fitnesses[names.index(k)] >= threshold
        }

    def crossover_mutation(self, gene_1: typing.Dict, gene_2: typing.Dict) -> typing.Dict:
        child_gene = {}
        for gene_name in gene_1.keys():
            child_gene[gene_name] = np.random.choice([gene_1[gene_name], gene_2[gene_name]])
            if np.random.rand() < self.config['mutation_rate']:
                child_gene[gene_name] = np.random.choice(self.space[gene_name])
        return child_gene
    
    def main(self):
        self.generate_initial_population()
        for generation_ind in range(1, self.config['iteration']+1):
            parents = self.selection(self.generation_database[-1])
            alphas: typing.Dict[str, alpha_lib.Alpha] = {}
            for child_ind in range(self.config['population']):
                child_name = self.generate_alpha_name(self.name, generation_ind, child_ind)
                parents_names = list(np.random.choice(list(parents.keys()), 2))
                child_gene = self.crossover_mutation(self.gene_database[parents_names[0]], self.gene_database[parents_names[1]])
                self.gene_database[child_name] = child_gene
                expr = self.template
                for gene_name, gene_val in self.gene_database[child_name].items():
                    expr = expr.replace(gene_name, gene_val)
                alphas[child_name] = alpha_lib.Alpha(
                    child_name,
                    payload={
                        "type": "REGULAR",
                        "settings": self.settings,
                        "regular": expr
                    }
                )
                alphas[child_name].to_disk()
            finish_alphas = self.collect_alphas(alphas)
            self.generation_database.append(finish_alphas)
              
if __name__ == '__main__':
    ga = GeneticAlgo(
        name='20240902_test_ga_008',
        template=TEMPLATE,
        space=SPACE,
        settings=SETTINGS,
        config=CONFIG
    )
    ga.main()
