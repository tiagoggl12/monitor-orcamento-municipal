-- Adiciona coluna valores_por_area_json à tabela investimento_regional
-- Para armazenar a divisão de valores por área de atuação

ALTER TABLE investimento_regional 
ADD COLUMN IF NOT EXISTS valores_por_area_json TEXT;

-- Comentário para documentação
COMMENT ON COLUMN investimento_regional.valores_por_area_json IS 
'JSON com valores por área: {"infraestrutura": 221831234.00, "saude": 110915617.00, "educacao": 138644522.00, "social": 83186713.00, "urbanismo": 0.00, "cultura": 0.00}';

