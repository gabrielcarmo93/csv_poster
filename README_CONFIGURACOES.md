# 💾 Sistema de Persistência de Configurações

## 📋 Visão Geral

O CSV Poster agora possui um sistema inteligente de persistência que salva automaticamente suas configurações para melhorar a experiência do usuário.

## 🔄 Funcionalidades

### ✅ Configurações Salvas Automaticamente:
- **Tema da aplicação** (claro/escuro)
- **URL do endpoint** principal
- **Método HTTP** (GET/POST)
- **Nível de concorrência**
- **Delimitador do CSV** (vírgula, ponto-e-vírgula, etc.)
- **Configurações de autenticação**:
  - Status (ativado/desativado)
  - URL de autenticação
  - Client ID
  - **Client Secret** (salvo automaticamente para conveniência)
  - Token JSONPath

### ❌ Configurações NÃO Salvas:
- **Arquivo CSV** selecionado (apenas configurações persistem)

## 🚀 Como Funciona

### Salvamento Automático:
- **Ao alterar tema**: Salva imediatamente
- **Ao sair de campos**: Salva quando você clica fora do campo
- **Ao fechar aplicação**: Salva todas as configurações atuais
- **Ao alterar opções**: Salva automaticamente (método HTTP, autenticação)

### Carregamento Automático:
- **Na inicialização**: Carrega configurações da sessão anterior
- **Aplicação automática**: Todos os campos são preenchidos automaticamente
- **Tema preservado**: O tema escolhido é mantido entre sessões

## 📁 Arquivo de Configuração

**Localização**: `user_config.json` (na pasta raiz do projeto)

**Formato**: JSON com timestamp da última atualização

**Exemplo**:
```json
{
  "theme": "superhero",
  "endpoint_url": "https://api.exemplo.com/upload",
  "method": "POST",
  "concurrency": "10",
  "delimiter": ";",
  "auth_enabled": true,
  "auth_url": "https://auth.exemplo.com/token",
  "client_id": "meu_client_id",
  "client_secret": "meu_client_secret",
  "token_path": "$.access_token",
  "last_updated": "2025-09-19T03:25:35.304520"
}
```

## 🎯 Benefícios

1. **⏱️ Economia de Tempo**: Não precisa reconfigurar a cada uso
2. **🔧 Configuração Persistente**: Mantém suas preferências entre sessões
3. **🎨 Tema Personalizado**: Seu tema favorito é lembrado
4. **🔐 Conveniência**: Todas as configurações salvas automaticamente
5. **📊 Produtividade**: Foco no trabalho, não na configuração

## 🔧 Dicas de Uso

- **Primeira vez**: Configure uma vez e suas preferências ficarão salvas
- **Mudança de projeto**: Apenas selecione novo CSV, outras configurações permanecem
- **Reset manual**: Delete `user_config.json` para restaurar padrões
- **Backup**: Copie `user_config.json` para preservar configurações

---

*Sistema implementado em 19/09/2025 - Versão 2.0 do CSV Poster*