# Plano de manutenção industrial

Sistema web leve para gestão de manutenção preventiva e corretiva.

## Funcionalidades

- **Equipamentos**: cadastro, edição e exclusão
- **Materiais**: cadastro de peças e itens do almoxarifado
- **Materiais x Equipamentos**: vínculo de componentes por equipamento
- **Ordens de Manutenção**: abertura e acompanhamento de serviços
- **Notificações**: registro de falhas e manutenções não planejadas
- **Histórico**: ocorrências e intervenções por equipamento

## Tecnologias

- Python 3
- Flask
- SQLite
- HTML + CSS

## Como rodar

```bash
git clone https://github.com/sandroeng23/Gerenciamento_manutencao_em_python.git
cd Gerenciamento_manutencao_em_python
python3 -m pip install flask
python3 mini_sap_pm_web.py
```

Acesse: http://localhost:8080

## Uso

- Cadastre os equipamentos na aba **Equipamentos**
- Cadastre os materiais em **Materiais**
- Faça vínculos em **Materiais x Equip.**
- Controle ordens, notificações e histórico nas abas correspondentes

## Observações

- O banco de dados é local (`sap_pm.db`), sem dependência externa
- Projeto para uso interno e pequenas operações de manutenção
