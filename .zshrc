# =========================================================================
# .zshrc
#
#
# =========================================================================

# -------------------------------------------------------------------------
# プロンプト
#
# -------------------------------------------------------------------------

    PROMPT="[zsh %n@%m]%(#.#.$) "
    bindkey -e
    PATH=/sbin:/usr/local/bin:/bin:/usr/local/sbin:$PATH:/usr/sbin
    export PATH
    export LANG=ja_JP.UTF-8
    source ~/project/Dev/share/etc/mf-dev.zshrc

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

# -------------------------------------------------------------------------
# alias
#
# -------------------------------------------------------------------------
    alias ls='ls --color'
    alias ll="ls -l"
    alias la="ls -la"

    # xselのクリップボードをmacのクリップボードと同じコマンドに
    alias pbcopy='xsel --clipboard --input'
    alias pbpaste='xsel --clipboard --input'

    #tmux
    alias tmux-copy='tmux save-buffer - | pbcopy'

export PATH="$HOME/.rbenv/bin:$PATH"
eval "$(rbenv init -)"



# lscolor
export LSCOLORS=CxGxcxdxCxegedabagacad

# git completion
#autoload bashcompinit
#bashcompinit
#source ~/git-completion.bash

#autoload -Uz vcs_info
#zstyle ':vcs_info:*' formats '(%s)-[%b]'
#zstyle ':vcs_info:*' actionformats '(%s)-[%b|%a]'
#precmd () {
#  psvar=()
#  LANG=en_US.UTF-8 vcs_info
#  [[ -n "$vcs_info_msg_0_" ]] && psvar[1]="$vcs_info_msg_0_"
#}
#RPROMPT="%1(v|%F{green}%1v%f|)"
#
export PATH="~/bin:/usr/local/gnu/bin:/usr/local/app/tmux/bin:$PATH"

export BIN_PATH="/usr/local/bin"
