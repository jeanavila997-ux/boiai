-- Seed do dicionário canônico de características.
-- ATENÇÃO: os códigos por programa abaixo são o ponto de partida
-- usado no motor de scoring; valide contra os sumários oficiais
-- Geneplus/PMGZ/ANCP da edição vigente antes de produção.
USE boiai;

INSERT INTO trait_dictionary (concept_key, grp, unit, direction, code_geneplus, code_pmgz, code_ancp, label) VALUES
 ('IPP',     'REPRODUCAO',  '%',   'MAIOR_MELHOR', 'IPP',      'IPP',    'IPP',   'Índice de Precocidade de Parto'),
 ('HP_STAY', 'REPRODUCAO',  '%',   'MAIOR_MELHOR', 'HP',       'STAY',   'HP',    'Habilidade de Permanência / Stayability'),
 ('PES',     'REPRODUCAO',  NULL,  'MAIOR_MELHOR', 'PES',      'PES',    'PES',   'Precocidade Escrotal'),
 ('PN',      'CRESCIMENTO', 'kg',  'MENOR_MELHOR', 'PN',       'PN',     'PN',    'Peso ao Nascer'),
 ('PD',      'CRESCIMENTO', 'kg',  'MAIOR_MELHOR', 'P210',     'PD',     'P205',  'Peso à Desmama'),
 ('PS',      'CRESCIMENTO', 'kg',  'MAIOR_MELHOR', 'P365',     'PS',     'P365',  'Peso ao Sobreano'),
 ('PE_450D', 'CRESCIMENTO', 'kg',  'MAIOR_MELHOR', 'P450',     'P450',   'P450',  'Peso aos 450 Dias'),
 ('TMD',     'MATERNO',     'kg',  'MAIOR_MELHOR', 'TMD',      'TMD',    'TMD',   'Taxa de Maternal / Desmama'),
 ('AOL',     'CARCACA',     'cm2', 'MAIOR_MELHOR', 'AOLg',     'AOL',    'AOL',   'Área de Olho de Lombo'),
 ('EGS',     'CARCACA',     'mm',  'MAIOR_MELHOR', 'EGSg',     'EGS',    'EGS',   'Espessura de Gordura Subcutânea'),
 ('MAR',     'CARCACA',     '%',   'MAIOR_MELHOR', 'MARg',     'MAR',    'MAR',   'Marmoreio')
ON DUPLICATE KEY UPDATE label = VALUES(label);

-- Personas padrão do agente (globais)
INSERT INTO agent_persona (nome, descricao, system_prompt, tom, verbosidade, proatividade, is_default)
SELECT * FROM (
  SELECT 'Zootecnista técnico' AS nome,
         'Interpreta DEPs e índices com rigor técnico, cita programas e edições.' AS descricao,
         'Você é o zootecnista do BoiAI, especialista em melhoramento genético de bovinos de corte (Nelore e zebuínos). Interprete DEPs e índices (Geneplus, PMGZ, ANCP), compare touros e matrizes e sugira acasalamentos dirigidos. Responda em português do Brasil, com precisão técnica. Quando faltar dado, diga qual informação é necessária. Nunca invente números de DEP.' AS system_prompt,
         'tecnico' AS tom, 'detalhado' AS verbosidade, 'sugere' AS proatividade, 1 AS is_default
  UNION ALL
  SELECT 'Capataz prático',
         'Linguagem direta de fazenda, foco em ação e números do dia a dia.',
         'Você é o capataz digital do BoiAI. Fale a língua da fazenda: direto, prático, sem enrolação. Foque no que precisa ser feito, em números concretos (peso, arroba, preço) e em prazos. Ao sugerir algo, diga o porquê em uma frase.',
         'direto', 'curto', 'proativo', 0
  UNION ALL
  SELECT 'Consultor de negócios',
         'Visão financeira: custo por arroba, margem, retorno por acasalamento.',
         'Você é o consultor de negócios do BoiAI. Analise a pecuária como negócio: custo por arroba produzida, margem por lote, retorno genético esperado por acasalamento e priorização de investimentos. Traga sempre o impacto em R$.',
         'formal', 'medio', 'sugere', 0
) AS seed
WHERE NOT EXISTS (SELECT 1 FROM agent_persona LIMIT 1);
