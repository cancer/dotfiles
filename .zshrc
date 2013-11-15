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

NPM_PATH=/usr/local/share/npm/bin
PATH="$NPM_PATH:/sbin:/usr/local/bin:/bin:/usr/local/sbin:$PATH:/usr/sbin"
export PATH
export PATH="/Users/y-uno/bin:/usr/local/gnu/bin:/usr/local/app/tmux/bin:$PATH"
export BIN_PATH="/usr/local/bin"

if [ -f "~/project/Dev/share/etc/mf-dev.zshrc" ]; then
  . ~/project/Dev/share/etc/mf-dev.zshrc
fi


# -------------------------------------------------------------------------
# プロンプト
#
# -------------------------------------------------------------------------

autoload colors
colors

# vcs_infoでgitのbranchとか表示する
if [ $(echo $OSTYPE |grep darwin |wc -l ) != 0 ]; then
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
else
  # プロンプトが表示される度に実行
  setopt prompt_subst
  precmd () {
    p_cdir="%{${fg[yellow]}%}%~%{${reset_color}%}"
    p_window=${WINDOW:+" $WINDOW "}
    if [ -z "${SSH_CONNECTION}" ]; then
      p_info="[%n@%m$p_window]"
    else
      p_info="%{${fg[green]}%}[%n@%m$p_window]%{${reset_color}%}"
    fi
  }
  RPROMPT='$p_cdir'
fi


PROMPT='$p_info%(#.#.$) '
PROMPT2='[%n]> ' 

#PROMPT="[zsh %n@%m]% "

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
alias -g G='| grep'
alias -g GI='| grep -i'
alias -g T='| tail'
alias -g TF='| tail -f'

# -------------------------------------------------------------------------
# function
#
# -------------------------------------------------------------------------

# scpのショートカット
function scpf { scp $1 y-uno@y-uno.dev.mf.local:~/tmp }
function scpd { scp -r $1 y-uno@y-uno.dev.mf.local:~/tmp }

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

# Linuxでもpbcopyを使いたい
case ${OSTYPE} in
  linux*)
    alias pbcopy='xsel --clipboard --input'
    alias pbpaste='xsel --clipboard --input'
    ;;
esac

#tmuxでpbcopy
alias tmux-copy='tmux save-buffer - | pbcopy'


# rbenv
which rbenv > /dev/null 2>&1 
if [ $? -eq 0 ]; then

	export PATH="$HOME/.rbenv/bin:$PATH"
	eval "$(rbenv init -)"

fi

# anyenv
which anyenv > /dev/null 2>&1 
if [ $? -eq 0 ]; then
  export PATH="$HOME/.anyenv/bin:$PATH"
  eval "$(anyenv init -)"
fi
