{{ config(
    severity='error',
    tags=['escopo_adicao'],
    meta={'escopo': 'adicao'}
) }}

-- ADR-0008, emenda R4-01: casos conhecidos da máscara `mascarar_cpf_no_nome` (CPFs sintéticos com DV
-- válido). Retorna uma linha por caso cuja saída diverge da esperada. Cobre CPF no fim com e sem
-- espaço, no começo, no meio, dois CPFs separados por um espaço (segunda passada), o nome que é só o
-- CPF, e trechos de 10 e 12 dígitos, que não são CPF e ficam como estão.
with casos (entrada, esperado) as (
  values
  ('JOAO DA SILVA 52998224725', 'JOAO DA SILVA ***.***.***-**'),
  ('JOAO DA SILVA52998224725', 'JOAO DA SILVA***.***.***-**'),
  ('52998224725 JOAO DA SILVA', '***.***.***-** JOAO DA SILVA'),
  ('JOAO 52998224725 ME', 'JOAO ***.***.***-** ME'),
  ('A 52998224725 11144477735', 'A ***.***.***-** ***.***.***-**'),
  ('52998224725', '***.***.***-**'),
  ('LOJA 1234567890', 'LOJA 1234567890'),
  ('LOJA 123456789012', 'LOJA 123456789012'),
  ('TINTAS FUNDÃO', 'TINTAS FUNDÃO')
)

select
  entrada,
  esperado,
  {{ mascarar_cpf_no_nome('entrada') }} as obtido
from casos
where {{ mascarar_cpf_no_nome('entrada') }} is distinct from esperado
