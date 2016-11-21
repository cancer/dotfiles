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

" -----------------------
" dein settings
" -----------------------

let s:dein_plugin_dir = expand('~/dotfiles/.vimbundle')
let s:dein_install_dir = s:dein_plugin_dir . '/repos/github.com/Shougo/dein.vim'
execute 'set runtimepath^=' . s:dein_install_dir

if dein#load_state(s:dein_install_dir)
  call dein#begin(expand('~/dotfiles/.vimbundle/'))

  call dein#load_toml('~/dotfiles/.dein.toml', {'lazy': 0})
  call dein#load_toml('~/dotfiles/.dein_lazy.toml', {'lazy': 1})

  call dein#end()
  call dein#save_state()
endif

if !has('vim_starting')
  if  dein#check_install()
    " Installation check.
    call dein#install()
  endif

  call dein#call_hook('source')
  call dein#call_hook('post_source')

  filetype plugin indent on
  syntax enable
endif



" -----------------------
" vimproc にpathを通す
" -----------------------

if has('win64')
  let g:vimproc_dll_path = $VIM . '/runtime/bundle/vimproc/autoload/vimproc_win64.dll'
endif


" -----------------------
" _vimrcを良い感じに開く
" -----------------------

let os=substitute(system('uname'), '\n', '', '')
let isMac=os=='Darwin' || os=='Mac'
if has('win64')
  let s:vimrcbody = '$VIM/_vimrc'
  let s:gvimrcbody = '$VIM/_gvimrc'
elseif isMac
  let s:vimrcbody = '$HOME/.vimrc'
  let s:gvimrcbody = '$HOME/.gvimrc'
elseif os=='Unix'
  let s:vimrcbody = '$HOME/vimrc'
  let s:gvimrcbody = '$HOME/gvimrc'
endif
let $MYVIMRC = expand(s:vimrcbody)
let $MYGVIMRC = expand(s:gvimrcbody)

function! OpenFile(file)
  let empty_buffer = line('$') == 1 && strlen(getline('1')) == 0
  if empty_buffer && !&modified
    execute 'e ' . a:file
  else
    execute 'tabnew ' . a:file
  endif
endfunction
command! OpenMyVimrc call OpenFile(s:vimrcbody)
command! OpenMyGVimrc call OpenFile(s:gvimrcbody)

if has('unix')
  nnoremap ,, :OpenMyVimrc<CR>
else
  nnoremap ,, :<C-u>OpenMyVimrc<CR>
  nnoremap ,<Tab> :<C-u>OpenMyGVimrc<CR>
endif


" -----------------------
" F5でリロード
" -----------------------

function! SourceIfExists(file)
  if filereadable(expand(a:file))
    execute 'source ' . a:file
  endif
  echo 'Reloaded vimrc and gvimrc and ' . a:file . '.'
  if has('win32') || has('win64')
    FullScreen
  endif
endfunction
if has('win32') || has('win64')
  nnoremap <F5> <Esc>:<C-u>source $MYVIMRC<CR> :source $MYGVIMRC<CR> :call SourceIfExists($FTPLUGIN .'¥'. &filetype . '.vim')<CR>
else
  nnoremap <F5> <Esc>:<C-u>source $MYVIMRC<CR> :call SourceIfExists($FTPLUGIN .'¥'. &filetype . '.vim')<CR>
endif

" Map double-tap Esc to clear search highlights
nnoremap <silent> <Esc><Esc> <Esc>:nohlsearch<CR><Esc>



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

" -----------------------
" 全角スペース・行末のスペース・タブの可視化
" -----------------------

if has("syntax")
    syntax on

   " PODバグ対策
    syn sync fromstart

    function! ActivateInvisibleIndicator()
        " 下の行の"　"は全角スペース
        syntax match InvisibleJISX0208Space "　" display containedin=ALL
        highlight InvisibleJISX0208Space term=underline ctermbg=Blue guibg=darkgray gui=underline
    endf
    augroup invisible
        autocmd! invisible
        autocmd BufNew,BufRead * call ActivateInvisibleIndicator()
    augroup END
endif

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
" FuzzyFinderから長いパスの中間を省略する関数をパクって最適化する
" http://hail2u.net/blog/software/optimize-vim-statusline.html
" -----------------------

function! SnipMid(str, len, mask)
  if a:len >= len(a:str)
    return a:str
  elseif a:len <= len(a:mask)
    return a:mask
  endif

  let len_head = (a:len - len(a:mask)) / 2
  let len_tail = a:len - len(a:mask) - len_head

  return (len_head > 0 ? a:str[: len_head - 1] : '') . a:mask . (len_tail > 0 ? a:str[-len_tail :] : '')
endfunction


" -----------------------
" ステータスラインに文字コードと改行文字を表示する
" -----------------------

set laststatus=2

"---------------------------------------------------------------------------
" ファイル設定関連

" -----------------------
" fileencode を設定
" -----------------------

set fileencodings=utf-8,euc-jp,sjis,cp932

" markdown
au BufNewFile,BufRead *.md setfiletype markdown
" coffeescript
au BufNewFile,BufRead *.coffee setfiletype coffeescript
" handlebars
au BufNewFile,BufRead *.hbs setfiletype html
" jade
au BufNewFile,BufRead *.jade setfiletype jade
" jsx
au BufNewFile,BufRead *.cjsx setfiletype coffee

" -----------------------
" vimshellエンコーディングエラー対策
" -----------------------
"Windows7ターミナル内はsjisなので

if has('win64')
	set termencoding=sjis
endif

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

"---------------------------------------------------------------------------
" プラグイン管理

" -----------------------
" NeoBundleの読み込み/設定
" -----------------------

"filetype plugin indent off
"
"if has('vim_starting')
"  if &compatible
"    set nocompatible
"  endif
"  set runtimepath+=~/dotfiles/.vimbundle/neobundle.vim/
"endif
"
"call neobundle#begin(expand('~/dotfiles/.vimbundle/'))
"
"" Let NeoBundle manage NeoBundle
"NeoBundleFetch 'Shougo/neobundle.vim'
"
"" originalrepos on github
"NeoBundle 'Shougo/vimproc', {
"\ 'build' : {
"\     'mac' : 'make -f make_mac.mak',
"\    },
"\ }
"NeoBundle 'Shougo/unite.vim.git'
"NeoBundle 'ujihisa/unite-colorscheme'
"NeoBundle 'Shougo/neocomplcache'
"NeoBundle 'Shougo/neosnippet'
"NeoBundle 'Shougo/neosnippet-snippets'
"NeoBundle 'Shougo/vimshell'
"NeoBundle 'Shougo/vimfiler.vim'
"NeoBundle 'ujihisa/vimshell-ssh'
"NeoBundle 'nathanaelkane/vim-indent-guides'
"NeoBundle 'tpope/vim-fugitive'
"NeoBundle 'editorconfig/editorconfig-vim'
"NeoBundle 'itchyny/lightline.vim'
"NeoBundle 'airblade/vim-gitgutter'
"NeoBundle 'Lokaltog/powerline', { 'rtp' : 'powerline/bindings/vim'}
"NeoBundle 'mattn/emmet-vim'
"NeoBundle 'Lokaltog/vim-easymotion'
"NeoBundle 'lilydjwg/colorizeR'
"NeoBundle "thinca/vim-quickrun"
"NeoBundle "jceb/vim-hier"
"NeoBundle "dannyob/quickfixstatus"
"NeoBundle 'leafgarland/typescript-vim'
"NeoBundle 'jason0x43/vim-js-indent'
"NeoBundle 'clausreinke/typescript-tools.vim'
"NeoBundle 'Quramy/tsuquyomi'
"
"" vim-scripts repos
"NeoBundle 'L9'
"NeoBundle 'FuzzyFinder'
"NeoBundle 'surround.vim'
"
"" colorschemes & syntaxes
"NeoBundle 'altercation/vim-colors-solarized'
"NeoBundle 'croaker/mustang-vim'
"NeoBundle 'jeffreyiacono/vim-colors-wombat'
"NeoBundle 'nanotech/jellybeans.vim'
"NeoBundle 'vim-scripts/Lucius'
"NeoBundle 'vim-scripts/Zenburn'
"NeoBundle 'mrkn/mrkn256.vim'
"NeoBundle 'jpo/vim-railscasts-theme'
"NeoBundle 'therubymug/vim-pyte'
"NeoBundle 'tomasr/molokai'
"NeoBundle 'kchmck/vim-coffee-script'
"NeoBundle 'digitaltoad/vim-jade'
"NeoBundle 'mxw/vim-jsx'
"
"call neobundle#end()
"
"filetype plugin indent on     " required!
"
"
"" If there are uninstalled bundles found on startup,
"" this will conveniently prompt you to install them.
"NeoBundleCheck

" -----------------------
" end setup
" -----------------------
set laststatus=2
if !has('gui_running')
  set t_Co=256
endif
set ambiwidth=double
