# =========================================================================
# .zshrc
#
#
# =========================================================================

# -------------------------------------------------------------------------
# 文字コード
#
# -------------------------------------------------------------------------

export LANG=ja_JP.UTF-8

# -------------------------------------------------------------------------
# PATH
#
# -------------------------------------------------------------------------

typeset -U path   # 重複を自動排除

path=(
  $HOME/.local/share/uv
  /opt/homebrew/bin
  /sbin
  /usr/local/bin
  /bin
  /usr/local/sbin
  $path             # 既存の継承分
  /usr/sbin
  $HOME/bin
  $HOME/dotfiles/node_modules/.bin
)

# direnv
eval "$(direnv hook zsh)"

export EDITOR="nvim"

# -------------------------------------------------------------------------
# プロンプト
#
# -------------------------------------------------------------------------

autoload colors
colors

# vcs_infoでgitのbranchとか表示する
autoload -Uz vcs_info
zstyle ':vcs_info:*' enable git svn
zstyle ':vcs_info:git:*' check-for-changes true
zstyle ':vcs_info:git:*' stagedstr "+"
zstyle ':vcs_info:git:*' unstagedstr "*"
# %s:vcs名 %b:branch名 %c:stagedstr %u unstagedstr
zstyle ':vcs_info:*' formats "%{${fg[red]}%}(%s %b%{${fg[cyan]}%}%c%u%{${fg[red]}%}) %{$reset_color%}"

# プロンプトが表示される度に実行
setopt prompt_subst
precmd () {
  LANG=en_US.UTF-8 vcs_info
  p_cdir="%{${fg[yellow]}%}%~%{${reset_color}%}"
  p_window=${WINDOW:+" $WINDOW "}
  if [ -z "${SSH_CONNECTION}" ]; then
    p_info="[%n@%m$p_window]"
  else
    p_info="%{${fg[green]}%}[%n@%m$p_window]%{${reset_color}%}"
  fi
}
RPROMPT='$p_cdir ${vcs_info_msg_0_}'


PROMPT='$p_info%(#.#.$) '
PROMPT2='[%n]> ' 

bindkey -e

# -------------------------------------------------------------------------
# 履歴
#
# -------------------------------------------------------------------------

# 履歴をファイルに保存する
HISTFILE=$HOME/.zsh_history

# メモリ内の履歴の数
HISTSIZE=10000

# 保存される履歴の数
SAVEHIST=10000

# 履歴ファイルに時刻を記録
setopt extended_history

# 全履歴の一覧を出力する
function history-all { history -E 1 }

# 直前と同じコマンドラインはヒストリに追加しない
setopt hist_ignore_dups

# コマンド行の余計な空白を詰めて履歴に入れる
setopt hist_reduce_blanks

# -------------------------------------------------------------------------
# 補完
#
# -------------------------------------------------------------------------

# 基本
autoload -U compinit
compinit

# 補完候補の大文字小文字の違いを無視
zstyle ':completion:*' matcher-list 'm:{a-z}={A-Z}'

# 補完候補を←↓↑→で選択
zstyle ':completion:*:default' menu select true

# 指定したコマンド名がなく、ディレクトリ名と一致した場合 cd する
# setopt auto_cd

# 補完候補が複数ある時に、一覧表示する
# setopt auto_list

# auto_list の補完候補一覧で、ls -F のようにファイルの種別をマーク表示
setopt list_types

# 補完に色を付ける
zstyle ':completion:*' list-colors 'di=36' 'ln=35' 'ex=32'

# -------------------------------------------------------------------------
# その他
#
# -------------------------------------------------------------------------

# コマンドラインの引数で --prefix=/usr などの = 以降でも補完できる
setopt magic_equal_subst

# 改行なくても表示
unsetopt promptcr

# Ctrl + D でログアウトしない
setopt ignore_eof

# Ctrl+S/Ctrl+Q によるフロー制御を使わないようにする
setopt NO_flow_control

# コマンドラインでも # 以降をコメントと見なす
setopt interactive_comments

# シェルが終了しても裏ジョブに HUP シグナルを送らないようにする
setopt NO_hup

# zmvを使う
autoload -Uz zmv
alias rename='noglob zmv -W'

# any env

## Node.js
eval "$(fnm env --use-on-cd)"

## bun
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"

## bun completions
[ -s "/Users/cancer/.bun/_bun" ] && source "/Users/cancer/.bun/_bun"


# OS Xのクイックルックでテキストのコピペを有効にする
if [ $(echo $OSTYPE |grep darwin |wc -l ) != 0 ]; then
  QLEnableTextSelectionValue=$(defaults read com.apple.finder QLEnableTextSelection) >/dev/null 2>&1
  if [[ $QLEnableTextSelectionValue -ne 1 ]]; then
    echo "restart finder"
    defaults write com.apple.finder QLEnableTextSelection -bool TRUE
    killall Finder
  else
    echo "already enabled text selection"
  fi
fi

# -------------------------------------------------------------------------
# alias
#
# -------------------------------------------------------------------------

# ls
case ${OSTYPE} in
  darwin*)
    alias ls='ls -G'
    ;;
  linux*)
    alias ls='ls --color'
    ;;
esac

alias ll="ls -l"
alias la="ls -la"

# lscolor
export LSCOLORS=gxfxxxxxcxxxxxxxxxgxgx
export LS_COLORS='di=01;36:ln=01;35:ex=01;32'

# dotfiles
DOTFILES_BASE="~/dotfiles/"

# edit
alias vi="nvim"
alias edit="vi" 
alias ezshrc="edit $DOTFILES_BASE.zshrc"
alias evim="edit $DOTFILES_BASE.vimrc"
alias etmux="edit $DOTFILES_BASE.tmux.conf"

# source
alias szshrc="source $DOTFILES_BASE.zshrc"
alias svim="source $DOTFILES_BASE.vimrc"
alias stmux="source $DOTFILES_BASE.tmux.conf"

# global
alias -g L='|  less'
alias -g G='| ag'
alias -g GI='| ag -i'
alias -g T='| tail'
alias -g TF='| tail -f'
alias -g C='| pbcopy'

# The next line updates PATH for the Google Cloud SDK.
if [ -f '/Users/cancer/google-cloud-sdk/path.zsh.inc' ]; then . '/Users/cancer/google-cloud-sdk/path.zsh.inc'; fi

# The next line enables shell command completion for gcloud.
if [ -f '/Users/cancer/google-cloud-sdk/completion.zsh.inc' ]; then . '/Users/cancer/google-cloud-sdk/completion.zsh.inc'; fi

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

. "$HOME/.local/bin/env"

export PYENV_ROOT="$HOME/.pyenv"
[ -d "$PYENV_ROOT/bin" ] && export PATH="$PYENV_ROOT/bin:$PATH"
if command -v pyenv >/dev/null; then
  eval "$(pyenv init - zsh)"
  eval "$(pyenv virtualenv-init -)"
fi

# for Claude Code
export LANG="ja_JP.UTF-8"

[[ "$TERM_PROGRAM" == "kiro" ]] && . "$(kiro --locate-shell-integration-path zsh)"

source ~/.safe-chain/scripts/init-posix.sh # Safe-chain Zsh initialization script

alias xclaude="claude --permission-mode auto"
alias xcopilot="copilot --allow-all"
alias xcodex="codex --dangerously-bypass-approvals-and-sandbox"
alias xagy="agy --dangerously-skip-permissions"

# zoxide
eval "$(zoxide init zsh)"

# fzf
source <(fzf --zsh)

# tmux: 引数なしで呼んだ時、ディレクトリ名をセッション名にして開始
tmux() {
  if [ $# -eq 0 ]; then
    local dir=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
    local session_name=$(basename "$dir" | tr '.' '_')
    if command tmux has-session -t "$session_name" 2>/dev/null; then
      command tmux attach-session -t "$session_name"
    else
      command tmux new-session -s "$session_name"
    fi
  else
    command tmux "$@"
  fi
}


# Added by Antigravity CLI installer
export PATH="/Users/cancer/.local/bin:$PATH"

# opencode
export PATH=/Users/cancer/.opencode/bin:$PATH
