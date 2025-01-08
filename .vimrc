"---------------------------------------------------------------------------
" 環境設定

set sw=2 st=2 ts=2
scriptencoding utf-8
set encoding=utf-8
set fileencodings=utf-8,sjis,euc-jp,iso-2022-jp,cp932
set fileformats=unix,dos,mac
if 1 && filereadable($VIM . '/vimrc_local.vim')
  source $VIM/vimrc_kaoriya.vim
endif

"---------------------------------------------------------------------------
" 検索の挙動に関する設定:

" -----------------------
" インクリメンタルサーチ
" -----------------------
set incsearch

"---------------------------------------------------------------------------
" 編集に関する設定:
"
" -----------------------
" タブの画面上での幅
" -----------------------
set tabstop=2

" -----------------------
" タブ幅
" -----------------------
set softtabstop=2

" -----------------------
" タブを挿入するときの幅
" -----------------------
set shiftwidth=2

" -----------------------
" タブを半角スペースで
" -----------------------
set expandtab

"---------------------------------------------------------------------------
" GUI固有ではない画面表示の設定:

" -----------------------
" 行番号を非表示 (number:表示)
" -----------------------
set number

" -----------------------
" タブや改行を表示 (list:表示)
" -----------------------
set list

" -----------------------
" どの文字でタブや改行を表示するかを設定
" -----------------------
set listchars=tab:>-,extends:<,trail:-

colorscheme desert

"---------------------------------------------------------------------------
" ファイル操作に関する設定:

" -----------------------
" バックアップファイルの作成
" -----------------------
set nobackup

" -----------------------
" スワップファイルの作成
" -----------------------
set noswapfile

" ---------------------------------------------------------------------------
" 編集関連
"
set autoindent
set cindent
set showmatch
set backspace=indent,eol,start

" -----------------------
"クリップボードをOSと連携
" -----------------------

if isMac
  set clipboard=unnamed,autoselect
elseif has('win32') || has('unix')
  set clipboard=unnamed
endif

" undoの永続化
if has('persistent_undo')
  set undodir=~/.vim/.vimundo
  augroup vimrc-undofile
    autocmd!
    autocmd BufReadPre ~/* setlocal undofile
  augroup END
endif

" -----------------------
"カーソルを行頭、行末で止まらないようにする
" -----------------------
set whichwrap=b,s,h,l
set whichwrap=b,s,h,l,<,>,[,]

"---------------------------------------------------------------------------
" UI関連
" -----------------------
"入力モード時、ステータスラインのカラーを変更
" -----------------------

augroup InsertHook
autocmd!
autocmd InsertEnter * highlight StatusLine guifg=#ccdc90 guibg=#2E4340
autocmd InsertLeave * highlight StatusLine guifg=#2E4340 guibg=#ccdc90
augroup END


"---------------------------------------------------------------------------
" コンソールでのカラー表示のための設定(暫定的にUNIX専用)¥
if has('unix') && !has('gui_running') && !has('gui_macvim')
  let uname = system('uname')
  if uname =~? "linux"
    set term=builtin_linux
  elseif uname =~? "freebsd"
    set term=builtin_cons25
  elseif uname =~? "Darwin"
    set term=builtin_xterm
    "set term=beos-ansi
  else
    set term=builtin_xterm
  endif
  unlet uname
endif

"---------------------------------------------------------------------------
" コンソール版で環境変数$DISPLAYが設定されていると起動が遅くなる件へ対応
if !has('gui_running') && has('xterm_clipboard')
  set clipboard=exclude:cons\\\|linux\\\|cygwin\\\|rxvt\\\|screen
endif

" -----------------------
" ステータスラインに文字コードと改行文字を表示する
" -----------------------

set laststatus=2

"---------------------------------------------------------------------------
" ファイル設定関連

" -----------------------
" fileencode を設定
" -----------------------

" markdown
au BufNewFile,BufRead *.md setfiletype markdown

syntax on


"---------------------------------------------------------------------------
" キーマップ設定
" keymap
nnoremap ZZ <Nop>

" moving
nnoremap j gj
nnoremap k gk
nnoremap gj j
nnoremap gk k
noremap <Space>h <Home>
noremap <Space>l <End>

" Moving selection
xmap <C-k> :mo'<-- <CR> gv
xmap <C-j> :mo'>+ <CR> gv

" edit
inoremap <C-z> <Esc>

" brackets"
inoremap {} {}<LEFT>
inoremap [] []<LEFT>
inoremap () ()<LEFT>
inoremap "" ""<LEFT>
inoremap '' ''<LEFT>
inoremap <> <><LEFT>
inoremap :; : ;<LEFT>
inoremap []5 [% %]<LEFT><LEFT><LEFT>

" open new tab
nnoremap <c-n> :<c-u>tabnew<cr>

" change buffer
nnoremap gb :<C-u>bn<CR>
nnoremap gB :<C-u>bp<CR>
nnoremap cb :<C-u>bd<CR>

" VimShell
" シェルを起動
nnoremap <silent> ,vs :VimShell<CR>

" unixでBSで文字を消せるように
noremap  
noremap!  
noremap <BS> 
noremap! <BS> 

vnoremap > >gv
vnoremap < <gv

" -----------------------
" end setup
" -----------------------
" ftが自動認識されなかったときのために
if !&filetype
  filetype detect
endif

if !has('gui_running')
  set t_Co=256
endif
set ambiwidth=double
