-- =====================================================
-- BoiAI — Schema unificado (MySQL 8)
-- Fusão dos domínios BoiControl (comercial/lotes) e
-- CattleGen (genética/cruzamento) + camadas de IA.
-- Vetores de embedding ficam no Qdrant (payload referencia
-- o id da linha aqui), pois MySQL 8 não tem tipo vetorial.
-- =====================================================

CREATE DATABASE IF NOT EXISTS boiai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE boiai;

-- ---------- Núcleo ----------

CREATE TABLE IF NOT EXISTS farm (
  id            CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  nome          VARCHAR(120) NOT NULL,
  cidade_uf     VARCHAR(120),
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_user (
  id            CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  farm_id       CHAR(36) NOT NULL REFERENCES farm(id) ON DELETE CASCADE,
  nome          VARCHAR(120) NOT NULL,
  email         VARCHAR(190) NOT NULL UNIQUE,
  senha_hash    VARCHAR(255) NOT NULL,
  papel         ENUM('dono','gerente','operador') NOT NULL DEFAULT 'operador',
  persona_id    CHAR(36) NULL,             -- persona padrão do agente
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS produtor (
  id            CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  farm_id       CHAR(36) NOT NULL REFERENCES farm(id) ON DELETE CASCADE,
  nome          VARCHAR(120) NOT NULL,
  observacoes   TEXT,
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_produtor_farm (farm_id)
);

-- ---------- Animais e genética (domínio CattleGen) ----------

CREATE TABLE IF NOT EXISTS animal (
  id                    CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  farm_id               CHAR(36) NOT NULL REFERENCES farm(id) ON DELETE CASCADE,
  nome_exibicao         VARCHAR(120) NOT NULL,
  sexo                  ENUM('M','F') NOT NULL,
  raca                  VARCHAR(60) NOT NULL,
  categoria             ENUM('bezerro','bezerra','vaca','novilha','garrote','boi') NULL,
  categoria_registral   VARCHAR(30),
  serie_registro        VARCHAR(30),
  rgn                   VARCHAR(30),
  rgd                   VARCHAR(30),
  registro_composto     VARCHAR(60),
  data_nascimento       DATE,
  status                ENUM('ativo','vendido','morto','inativo') NOT NULL DEFAULT 'ativo',
  proprietario          VARCHAR(120),
  criador               VARCHAR(120),
  municipio_uf          VARCHAR(120),
  central_semen         VARCHAR(120),
  categoria_reprodutiva VARCHAR(60),       -- novilha/matriz/doadora
  genotipado            TINYINT(1) NOT NULL DEFAULT 0,
  consanguinidade_pct   DECIMAL(5,2),
  is_observed           TINYINT(1) NOT NULL DEFAULT 0,  -- catálogo importado em observação
  observacoes           TEXT,
  created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_animal_farm (farm_id),
  INDEX idx_animal_status (farm_id, status),
  INDEX idx_animal_nascimento (data_nascimento)
);

CREATE TABLE IF NOT EXISTS animal_relation (
  id                 CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  animal_id          CHAR(36) NOT NULL REFERENCES animal(id) ON DELETE CASCADE,
  relation_type      ENUM('PAI','MAE','AVO_MATERNO') NOT NULL,
  related_animal_id  CHAR(36) NULL REFERENCES animal(id),
  related_name       VARCHAR(120),          -- quando o parente não está cadastrado
  INDEX idx_relation_animal (animal_id),
  INDEX idx_relation_related (related_animal_id)
);

CREATE TABLE IF NOT EXISTS evaluation (
  id                  CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  animal_id           CHAR(36) NOT NULL REFERENCES animal(id) ON DELETE CASCADE,
  programa            ENUM('GENEPLUS','PMGZ','ANCP') NOT NULL,
  edicao              VARCHAR(60),          -- ex.: '2023-3'
  data_ref            DATE,
  base_genetica       VARCHAR(60),
  indice_resumo_nome  VARCHAR(30),          -- IQGg / iABCZg / MGTe
  indice_resumo_valor DECIMAL(12,4),
  rank_resumo_tipo    ENUM('PERCENTIL','DECA','TOP','CLASSE','NENHUM') NOT NULL DEFAULT 'NENHUM',
  rank_resumo_valor   DECIMAL(8,2),
  fonte_imagem        VARCHAR(500),
  raw_payload         JSON,                 -- trilha de auditoria
  created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_eval (animal_id, programa, edicao),
  INDEX idx_eval_animal (animal_id)
);

CREATE TABLE IF NOT EXISTS evaluation_trait (
  id             CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  evaluation_id  CHAR(36) NOT NULL REFERENCES evaluation(id) ON DELETE CASCADE,
  code           VARCHAR(40) NOT NULL,      -- código ORIGINAL do programa (AOLg, DAOLG...)
  label          VARCHAR(120),
  grp            ENUM('REPRODUCAO','CRESCIMENTO','CARCACA','FUNCIONAL','MATERNO') NULL,
  unit           VARCHAR(20),
  value          DECIMAL(14,5),             -- DEP na unidade da característica
  accuracy       DECIMAL(5,2),              -- 0-100
  rank_type      ENUM('PERCENTIL','DECA','TOP','CLASSE','NENHUM') NOT NULL DEFAULT 'NENHUM',
  rank_value     DECIMAL(8,2),
  classe         VARCHAR(20),
  direction      ENUM('MAIOR_MELHOR','MENOR_MELHOR') NOT NULL DEFAULT 'MAIOR_MELHOR',
  INDEX idx_trait_eval (evaluation_id)
);

-- Dicionário canônico: mapeia conceito -> código em cada programa
CREATE TABLE IF NOT EXISTS trait_dictionary (
  id             CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  concept_key    VARCHAR(40) NOT NULL UNIQUE,  -- ex.: 'AOL', 'IPP'
  grp            ENUM('REPRODUCAO','CRESCIMENTO','CARCACA','FUNCIONAL','MATERNO') NOT NULL,
  unit           VARCHAR(20),
  direction      ENUM('MAIOR_MELHOR','MENOR_MELHOR') NOT NULL DEFAULT 'MAIOR_MELHOR',
  code_geneplus  VARCHAR(40),
  code_pmgz      VARCHAR(40),
  code_ancp      VARCHAR(40),
  label          VARCHAR(120) NOT NULL
);

CREATE TABLE IF NOT EXISTS file_asset (
  id           CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  animal_id    CHAR(36) NULL REFERENCES animal(id) ON DELETE CASCADE,
  tipo         ENUM('FOTO','FICHA','PDF') NOT NULL DEFAULT 'FOTO',
  arquivo_url  VARCHAR(500) NOT NULL,
  origem       VARCHAR(60),
  created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_asset_animal (animal_id)
);

CREATE TABLE IF NOT EXISTS mating (
  id              CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  farm_id         CHAR(36) NOT NULL REFERENCES farm(id) ON DELETE CASCADE,
  sire_id         CHAR(36) NOT NULL REFERENCES animal(id),
  dam_id          CHAR(36) NOT NULL REFERENCES animal(id),
  programa_base   ENUM('GENEPLUS','PMGZ','ANCP') NOT NULL,
  objetivo        ENUM('NOVILHAS','REPOSICAO','TERMINAL') NOT NULL,
  politica        ENUM('ESTRITA','MEDIA_DISPONIVEL','IMPUTACAO_MEDIA_PROGRAMA') NOT NULL DEFAULT 'MEDIA_DISPONIVEL',
  score_composto  DECIMAL(6,2),
  confianca       DECIMAL(5,2),
  alertas         JSON,
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_mating_farm (farm_id),
  INDEX idx_mating_sire (sire_id),
  INDEX idx_mating_dam (dam_id)
);

CREATE TABLE IF NOT EXISTS mating_trait_result (
  id                CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  mating_id         CHAR(36) NOT NULL REFERENCES mating(id) ON DELETE CASCADE,
  trait_code        VARCHAR(40),
  sire_value        DECIMAL(14,5),
  dam_value         DECIMAL(14,5),
  expected_value    DECIMAL(14,5),
  normalized_score  DECIMAL(6,2),
  weight            DECIMAL(5,2),
  INDEX idx_mtr_mating (mating_id)
);

-- ---------- Comercial (domínio BoiControl) ----------

CREATE TABLE IF NOT EXISTS lote_compra (
  id                CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  farm_id           CHAR(36) NOT NULL REFERENCES farm(id) ON DELETE CASCADE,
  data              DATE NOT NULL,
  nome_lote         VARCHAR(120) NOT NULL,
  produtor_id       CHAR(36) NULL REFERENCES produtor(id),
  origem            VARCHAR(120),
  valor_por_kg_macho DECIMAL(10,2),
  valor_por_kg_femea DECIMAL(10,2),
  created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_lote_farm_data (farm_id, data)
);

CREATE TABLE IF NOT EXISTS item_lote (
  id           CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  lote_id      CHAR(36) NOT NULL REFERENCES lote_compra(id) ON DELETE CASCADE,
  animal_id    CHAR(36) NULL REFERENCES animal(id),   -- vínculo opcional ao cadastro
  id_animal    INT,                                   -- nº do animal dentro do lote
  sexo         ENUM('M','F') NOT NULL,
  categoria    ENUM('bezerro','bezerra','vaca','novilha','garrote','boi') NOT NULL,
  raca         VARCHAR(60),
  peso         DECIMAL(8,2),
  valor_total  DECIMAL(12,2),
  observacoes  TEXT,
  INDEX idx_item_lote (lote_id)
);

CREATE TABLE IF NOT EXISTS preco_kg_historico (
  id         CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  farm_id    CHAR(36) NOT NULL REFERENCES farm(id) ON DELETE CASCADE,
  data       DATE NOT NULL,
  categoria  VARCHAR(40),
  sexo       ENUM('M','F'),
  valor_kg   DECIMAL(10,2) NOT NULL,
  fonte      VARCHAR(120),
  INDEX idx_preco_farm_data (farm_id, data)
);

-- ---------- Manejo (novo) ----------

CREATE TABLE IF NOT EXISTS pesagem (
  id          CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  animal_id   CHAR(36) NOT NULL REFERENCES animal(id) ON DELETE CASCADE,
  data        DATE NOT NULL,
  peso_kg     DECIMAL(8,2) NOT NULL,
  origem      VARCHAR(60),               -- balança / fita / estimativa
  observacoes TEXT,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_pesagem_animal (animal_id, data)
);

CREATE TABLE IF NOT EXISTS evento_sanitario (
  id          CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  animal_id   CHAR(36) NOT NULL REFERENCES animal(id) ON DELETE CASCADE,
  data        DATE NOT NULL,
  tipo        ENUM('VACINA','VERMIFUGO','MEDICACAO','EXAME','OUTRO') NOT NULL,
  produto     VARCHAR(120),
  dose        VARCHAR(60),
  observacoes TEXT,
  INDEX idx_san_animal (animal_id, data)
);

CREATE TABLE IF NOT EXISTS evento_reprodutivo (
  id          CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  animal_id   CHAR(36) NOT NULL REFERENCES animal(id) ON DELETE CASCADE,  -- fêmea
  data        DATE NOT NULL,
  tipo        ENUM('COBERTURA','INSEMINACAO','DIAGNOSTICO','PARTO','DESMAMA','ABORTO') NOT NULL,
  sire_id     CHAR(36) NULL REFERENCES animal(id),
  resultado   VARCHAR(120),
  observacoes TEXT,
  INDEX idx_repro_animal (animal_id, data)
);

-- ---------- IA: chat, memória, persona, conhecimento ----------

CREATE TABLE IF NOT EXISTS agent_persona (
  id            CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  farm_id       CHAR(36) NULL REFERENCES farm(id) ON DELETE CASCADE, -- NULL = persona global
  nome          VARCHAR(80) NOT NULL,        -- ex.: 'Capataz prático'
  descricao     VARCHAR(255),
  system_prompt TEXT NOT NULL,
  tom           ENUM('formal','tecnico','direto','descontraido') NOT NULL DEFAULT 'direto',
  verbosidade   ENUM('curto','medio','detalhado') NOT NULL DEFAULT 'medio',
  proatividade  ENUM('reativo','sugere','proativo') NOT NULL DEFAULT 'sugere',
  modelo        VARCHAR(80),                 -- override do modelo Ollama
  think_level   ENUM('false','true','low','medium','high') NOT NULL DEFAULT 'medium',
  tools_ativas  JSON,                        -- lista de tools habilitadas; NULL = todas
  is_default    TINYINT(1) NOT NULL DEFAULT 0,
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_config (
  id                    CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  farm_id               CHAR(36) NOT NULL REFERENCES farm(id) ON DELETE CASCADE,
  memoria_sessao_on     TINYINT(1) NOT NULL DEFAULT 1,
  memoria_perfil_on     TINYINT(1) NOT NULL DEFAULT 1,
  memoria_semantica_on  TINYINT(1) NOT NULL DEFAULT 1,
  extracao_automatica   TINYINT(1) NOT NULL DEFAULT 1,  -- extrai fatos das conversas
  janela_contexto_msgs  INT NOT NULL DEFAULT 20,
  rag_top_k             INT NOT NULL DEFAULT 5,
  updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_config_farm (farm_id)
);

CREATE TABLE IF NOT EXISTS agent_memory (
  id          CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  farm_id     CHAR(36) NOT NULL REFERENCES farm(id) ON DELETE CASCADE,
  user_id     CHAR(36) NULL REFERENCES app_user(id) ON DELETE SET NULL,
  tipo        ENUM('perfil','fato','preferencia','decisao') NOT NULL,
  conteudo    TEXT NOT NULL,
  fixada      TINYINT(1) NOT NULL DEFAULT 0,   -- nunca expira nem é esquecida no recall
  expira_em   DATE NULL,                        -- TTL opcional
  origem      VARCHAR(60),                      -- 'manual' | 'chat' | 'importacao'
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_memory_farm (farm_id, tipo)
  -- embedding fica no Qdrant, coleção 'agent_memory', payload = id
);

CREATE TABLE IF NOT EXISTS chat_session (
  id          CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  farm_id     CHAR(36) NOT NULL REFERENCES farm(id) ON DELETE CASCADE,
  user_id     CHAR(36) NULL REFERENCES app_user(id) ON DELETE SET NULL,
  persona_id  CHAR(36) NULL REFERENCES agent_persona(id),
  titulo      VARCHAR(160),
  canal       ENUM('web','mobile','cli') NOT NULL DEFAULT 'web',
  arquivada   TINYINT(1) NOT NULL DEFAULT 0,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_session_farm (farm_id, created_at)
);

CREATE TABLE IF NOT EXISTS chat_message (
  id          CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  session_id  CHAR(36) NOT NULL REFERENCES chat_session(id) ON DELETE CASCADE,
  role        ENUM('system','user','assistant','tool') NOT NULL,
  content     MEDIUMTEXT,
  thinking    MEDIUMTEXT,
  tool_calls  JSON,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_msg_session (session_id, created_at)
);

-- Base de conhecimento do RAG (embeddings no Qdrant, coleção 'knowledge')
CREATE TABLE IF NOT EXISTS knowledge_document (
  id            CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  farm_id       CHAR(36) NULL REFERENCES farm(id) ON DELETE CASCADE, -- NULL = global
  fonte         VARCHAR(60) NOT NULL,   -- 'abcz_artigo' | 'pmgz_sumario' | 'ancp_doc' | 'nota_fazenda'
  titulo        VARCHAR(255),
  conteudo      MEDIUMTEXT NOT NULL,    -- chunk de ~800 tokens
  url           VARCHAR(500),
  publicado_em  DATETIME NULL,
  metadata      JSON,
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FULLTEXT KEY ft_knowledge (titulo, conteudo)
);

-- ---------- Importações e relatórios ----------

CREATE TABLE IF NOT EXISTS import_job (
  id             CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  farm_id        CHAR(36) NOT NULL REFERENCES farm(id) ON DELETE CASCADE,
  origem_tipo    ENUM('mysql','mysql_dump','excel','csv','indexeddb_json') NOT NULL,
  origem_detalhe VARCHAR(500),           -- host/banco ou nome do arquivo
  status         ENUM('mapeando','dry_run','executando','concluido','erro','revertido') NOT NULL DEFAULT 'mapeando',
  mapeamento     JSON,                   -- coluna origem -> destino
  relatorio      JSON,                   -- contagens, erros, avisos
  created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  finished_at    TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS report (
  id          CHAR(36) PRIMARY KEY DEFAULT (UUID()),
  farm_id     CHAR(36) NOT NULL REFERENCES farm(id) ON DELETE CASCADE,
  mating_id   CHAR(36) NULL REFERENCES mating(id) ON DELETE CASCADE,
  formato     VARCHAR(10),               -- pdf / xlsx / csv
  arquivo_url VARCHAR(500),
  gerado_em   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------- Configurações da fazenda (domínio BoiControl) ----------

CREATE TABLE IF NOT EXISTS configuracao (
  farm_id                CHAR(36) PRIMARY KEY REFERENCES farm(id) ON DELETE CASCADE,
  kg_por_arroba          DECIMAL(4,1) NOT NULL DEFAULT 15.0,
  nome_fazenda_principal VARCHAR(120),
  extras                 JSON
);
