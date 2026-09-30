# Legenda AI

**Kaique Dias · Python · Transcrição com IA · SRT e VTT**

[![Testes](https://github.com/DrKaiqueDias/legenda-ai/actions/workflows/tests.yml/badge.svg)](https://github.com/DrKaiqueDias/legenda-ai/actions/workflows/tests.yml)

Quero que legendar um vídeo seja uma tarefa simples. Você escolhe o arquivo, o programa reconhece a fala e entrega a legenda com os tempos marcados. Depois, é só revisar e abrir no player ou no editor que já usa.

Criei este projeto para aulas, entrevistas, apresentações e vídeos do dia a dia. Ele roda no computador, usa modelos prontos de reconhecimento de fala e não exige conta em uma API paga.

## O que ele faz

- Recebe um arquivo local de áudio ou vídeo, como MP3, WAV, M4A, FLAC, MP4, MOV ou MKV, desde que o codec seja reconhecido pelo decodificador.
- Detecta o idioma da fala ou usa o idioma que você informar.
- Gera **SRT**, **VTT**, uma transcrição em texto e um resumo da execução.
- Permite identificar mudanças de idioma dentro da mesma gravação.
- Tem uma opção para traduzir a fala para inglês.
- Mantém o arquivo original e nunca substitui uma pasta de saída existente.

**Sobre os idiomas:** o reconhecimento é multilíngue e depende do suporte do modelo Whisper. Português, inglês, espanhol, francês, alemão, japonês, árabe e vários outros estão incluídos. Não seria correto prometer todos os idiomas e dialetos do mundo. Por padrão, a legenda fica no idioma falado; `--ingles` traduz para inglês. Esta versão não traduz para qualquer idioma de destino.

## Comece por aqui

Use **Python 3.11, 3.12 ou 3.13, de 64 bits**. Recomendo começar pelo 3.12. A execução usa CPU, então não é preciso ter uma placa de vídeo dedicada. O modelo precisa de espaço em disco e memória; arquivos longos e modelos maiores exigem mais do computador.

### 1. Baixe o projeto

No GitHub, clique em **Code → Download ZIP**, extraia a pasta e abra um terminal dentro dela. Se já usa Git:

```bash
git clone https://github.com/DrKaiqueDias/legenda-ai.git
cd legenda-ai
```

### 2. Prepare o ambiente

**Windows — PowerShell:**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**Linux ou macOS:**

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

No Linux, talvez seja necessário instalar o pacote de suporte a `venv` da sua distribuição. Se aparecer “No matching distribution”, confira a versão e a arquitetura do Python.

### 3. Gere sua primeira legenda

No Windows:

```powershell
.\.venv\Scripts\python.exe legenda.py "meu video.mp4"
```

No Linux ou macOS:

```bash
.venv/bin/python legenda.py "meu video.mp4"
```

Troque `meu video.mp4` pelo caminho do seu arquivo. As aspas são importantes quando o nome tem espaços. Na primeira execução, o modelo é baixado para `.modelos`; esse download pode levar alguns minutos. Nas próximas, o programa reutiliza os arquivos.

### 4. Abra o resultado

Ao lado de `meu video.mp4`, será criada a pasta `meu video.legendas`:

```text
meu video.legendas/
  legendas.srt
  legendas.vtt
  transcricao.txt
  informacoes.json
```

Abra o vídeo no seu player e carregue `legendas.srt` como arquivo de legenda. Em um editor de vídeo, importe o SRT como faixa de legendas. O VTT é útil para players na web. O programa cria arquivos separados; ele não grava a legenda por cima da imagem.

### 5. Revise antes de publicar

Ouça os trechos com nomes próprios, números e termos técnicos. Confira também o início e o fim de cada legenda. Reconhecimento automático ajuda a ganhar tempo, mas ruído, sobreposição de vozes e sotaques podem gerar erros. A detecção de fala reduz transcrições em silêncio, sem eliminar completamente esse problema.

## Comandos que uso no dia a dia

Nos exemplos abaixo, `python` representa o Python do ambiente que você criou. No Windows, pode substituí-lo por `.\.venv\Scripts\python.exe`; no Linux/macOS, por `.venv/bin/python`.

**Informar que o áudio está em português:**

```bash
python legenda.py "entrevista.mp4" --idioma pt
```

`--idioma` informa o idioma da fala. Não é um comando de tradução.

**Usar um modelo maior:**

```bash
python legenda.py "aula.mp4" --modelo small --saida "aula_revisao"
```

Comece com `base`, que é o padrão. `tiny` exige menos recursos; `small`, `medium` e `large-v3` aumentam o custo de execução. Compare um trecho do seu próprio material antes de escolher. Um modelo maior não garante que todos os erros desaparecerão.

**Manter os idiomas de uma conversa multilíngue:**

```bash
python legenda.py "conversa.mp3" --multilingue
```

Essa opção tenta detectar o idioma a cada segmento. Ela não deve ser combinada com um idioma fixo. Mudanças muito curtas ou no meio de uma frase ainda podem falhar.

**Traduzir a fala para legendas em inglês:**

```bash
python legenda.py "aula.mp4" --idioma pt --ingles --saida "aula_ingles"
```

Na tradução, uso os tempos dos segmentos, pois as palavras traduzidas não têm correspondência direta com cada palavra falada. Os blocos podem ficar maiores e precisam de revisão.

**Rodar sem baixar nada:**

```bash
python legenda.py "aula.mp4" --offline --saida "aula_offline"
```

Baixe o mesmo modelo em uma execução anterior e mantenha a pasta `.modelos`. Para guardá-la em outro local, use `--modelos "caminho/para/modelos"` em ambas as execuções.

## Quando algo não funcionar

| Mensagem ou situação | O que fazer |
| :--- | :--- |
| Arquivo não encontrado | Confira o caminho e use aspas se houver espaços. Links de vídeos não são aceitos; use o arquivo local. |
| A pasta de saída já existe | Escolha outra com `--saida`. Isso protege legendas que você já revisou. |
| Nenhuma fala identificada | Confira se há uma faixa de áudio audível. Música, silêncio e fala muito baixa podem não produzir legendas. |
| Falha no primeiro download | Confira conexão e espaço em disco. `--offline` só funciona depois de o modelo estar disponível. |
| Erro ao abrir mídia | Verifique o codec e se o arquivo está íntegro. Se necessário, exporte o áudio como WAV ou MP3 no seu editor. |
| Está demorando | Teste `--modelo tiny` em um trecho curto. O programa processa a gravação antes de salvar o resultado; arquivos longos também usam mais memória. |
| O idioma saiu errado | Informe o idioma falado com `--idioma`, como `pt`, `es` ou `en`. |

## Como foi construído

A ferramenta usa [faster-whisper](https://github.com/SYSTRAN/faster-whisper), uma implementação do Whisper com CTranslate2. A leitura de mídia passa pelo PyAV, que traz bibliotecas FFmpeg nos pacotes binários usuais. A instalação padrão não pede um executável FFmpeg separado. Fixei o PyAV abaixo da versão 19 porque essa versão retirou um argumento ainda usado pelo faster-whisper 1.2.1. O modelo é baixado do Hugging Face; a inferência ocorre localmente. Os créditos do modelo e das bibliotecas continuam sendo dos respectivos projetos.

Meu código cuida da entrada, organização dos trechos, arquivos de saída e mensagens de uso. Os tempos vêm do modelo. Na transcrição, palavras são agrupadas com um alvo de até 80 caracteres ou seis segundos por bloco. Isso orienta a divisão, sem prometer um limite rígido: palavras longas, trechos sem alinhamento e correções de sobreposição podem ultrapassá-lo. Quebras de linha buscam 42 caracteres sem partir palavras longas. A aparência final depende do player e da escrita de cada idioma.

O programa não identifica quem está falando, não faz dublagem e não transcreve ao vivo. Quando existem várias faixas de áudio, a seleção segue o decodificador; exporte a faixa desejada separadamente se precisar controlar isso.

## Testes e contribuições

```bash
python -m unittest discover -v
python legenda.py --help
```

Os testes de lógica usam apenas a biblioteca padrão. Cobrem tempos, texto em UTF-8, SRT/VTT, preservação das palavras, entrada inválida e proteção dos arquivos existentes. A chamada ao modelo é simulada nesses testes; isso não mede a precisão do reconhecimento de fala. O teste de integração local usa uma gravação pública e o modelo `tiny`.

Para contribuir, descreva o problema, acrescente um teste quando houver mudança de comportamento e use um exemplo que possa ser compartilhado. Não envie gravações privadas em issues. A integração contínua verifica os testes em Windows e Linux; as Actions usam versões fixadas por commit.

**Autor: Kaique Dias.** Código sob licença MIT. Consulte [LICENSE](LICENSE).
