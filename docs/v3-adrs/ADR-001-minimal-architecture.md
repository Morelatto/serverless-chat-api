# ADR-001: Arquitetura Minimalista com Feature Única

**Status:** Aceito  
**Data:** 2025-01-04  

## Contexto

Microserviço para processar prompts, persistir dados, chamar LLM e retornar respostas. Foco em simplicidade e completude funcional.

## Decisão

Estrutura minimalista com uma única feature (chat) e componentes compartilhados.

```
src/
├── chat/           # Domínio único
├── shared/         # Infraestrutura compartilhada  
└── main.py         # Entry point
```

## Alternativas Consideradas

1. **Microserviços separados**: Rejeitado - complexidade desnecessária
2. **Monólito tradicional**: Rejeitado - sem separação de conceitos
3. **DDD completo**: Rejeitado - over-engineering para escopo

## Consequências

**Positivas:**
- Estrutura imediatamente compreensível
- Fácil navegação e manutenção
- Separação clara domínio vs infraestrutura
- Deploy único simplificado

**Negativas:**
- Menos flexível para múltiplos domínios futuros
- Acoplamento médio entre chat e shared

## Decisões Relacionadas

- FastAPI para desenvolvimento local
- Lambda handler integrado no main.py
- Testes focados na feature chat