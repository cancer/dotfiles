"---------------------------------------------------------------------------
" 環境設定

909090 nocompatible
set sw=2 st=2 ts=2
scriptencoding utf-8
set encoding=utf-8
set fileencodings=utf-8,sjis,euc-jp,iso-2022-jp,cp932
set fileformats=unix,dos,mac
if 1 && filereadable($VIM . '/vimrc_local.vim')
  source $VIM/vimrc_kaoriya.vim
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
        "syntax match InvisibleTrailedSpace "[ ¥t]¥+$" display containedin=ALL
        "highlight InvisibleTrailedSpace term=underline ctermbg=Red guibg=NONE gui=undercurl guisp=darkorange
        "syntax match InvisibleTab "¥t" display containedin=ALL
        "highlight InvisibleTab term=underline ctermbg=white gui=undercurl guisp=darkslategray
    endf
    augroup invisible
        autocmd! invisible
        autocmd BufNew,BufRead * call ActivateInvisibleIndicator()
    augroup END
endif

colorscheme desert
"colorscheme wombat
" wombatのVisualモードをdesert風(緑っぽいやつ)にする
if g:colors_name ==? 'wombat'
  hi Visual gui=none guifg=khaki guibg=olivedrab
endif

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
"set swapfile
"set directory=~/.vim/vim_swap/

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

"set statusline=%<%f¥ %m%r%h%w%{'['.(&fenc!=''?&fenc:&enc).']['.&ff.']'}%=%l,%c%V%8P

" set statusline=%{expand('%:p:t')}¥ %<¥(%{SnipMid(expand('%:p:h'),80-len(expand('%:p:t')),'...')}¥)%=¥ %m%r%y%w%{'['.(&fenc!=''?&fenc:&enc).']['.&ff.']'}[%3l,%3c]%8P

"set statusline=%<%f¥ %h%m%r%{fugitive#statusline()}%=%-14.(%l,%c%V%)¥ %P
set laststatus=2

"set statusline=%<%f¥ %m%r%h%w%{'['.(&fenc!=''?&fenc:&enc).']['.&ff.']'}%=%l,%c%V%8P

"set statusline=%{expand('%:p:t')}¥ %<¥(%{SnipMid(expand('%:p:h'),80-len(expand('%:p:t')),'...')}¥)%=¥ %m%r%y%w%{'['.(&fenc!=''?&fenc:&enc).']['.&ff.']'}[%3l,%3c]%8P

"set statusline=%<%f\ %m%r%h%w%{'['.(&fenc!=''?&fenc:&enc).']['.&ff.']'}%=%l,%c%V%8P

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

" edit
"noremap <CR> i<CR><ESC> " cwでファイルがEnterで開けなくなるのでやめる
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

filetype plugin indent off

if has('vim_starting')
  if &compatible
    set nocompatible
  endif
  set runtimepath+=~/dotfiles/.vimbundle/neobundle.vim/
endif

call neobundle#begin(expand('~/dotfiles/.vimbundle/'))

" Let NeoBundle manage NeoBundle
NeoBundleFetch 'Shougo/neobundle.vim'

" originalrepos on github
NeoBundle 'Shougo/vimproc', {
\ 'build' : {
\     'mac' : 'make -f make_mac.mak',
\    },
\ }
NeoBundle 'Shougo/unite.vim.git'
NeoBundle 'ujihisa/unite-colorscheme'
NeoBundle 'Shougo/neocomplcache'
NeoBundle 'Shougo/neosnippet'
NeoBundle 'Shougo/vimshell'
NeoBundle 'Shougo/vimfiler.vim'
NeoBundle 'ujihisa/vimshell-ssh'
NeoBundle 'nathanaelkane/vim-indent-guides'
NeoBundle 'tpope/vim-fugitive'
NeoBundle 'kchmck/vim-coffee-script'
NeoBundle 'editorconfig/editorconfig-vim'
NeoBundle 'itchyny/lightline.vim'
NeoBundle 'airblade/vim-gitgutter'
NeoBundle 'Lokaltog/powerline', { 'rtp' : 'powerline/bindings/vim'}
NeoBundle 'mattn/emmet-vim'
NeoBundle 'Lokaltog/vim-easymotion'
NeoBundle 'editorconfig/editorconfig-vim'
NeoBundle 'lilydjwg/colorizeR'
NeoBundle 'mxw/vim-jsx'

" vim-scripts repos
NeoBundle 'sudo.vim'
NeoBundle 'L9'
NeoBundle 'FuzzyFinder'
NeoBundle 'surround.vim'
NeoBundle 'visSum.vim'

" colorschemes & syntaxes
NeoBundle 'altercation/vim-colors-solarized'
NeoBundle 'croaker/mustang-vim'
NeoBundle 'jeffreyiacono/vim-colors-wombat'
NeoBundle 'nanotech/jellybeans.vim'
NeoBundle 'vim-scripts/Lucius'
NeoBundle 'vim-scripts/Zenburn'
NeoBundle 'mrkn/mrkn256.vim'
NeoBundle 'jpo/vim-railscasts-theme'
NeoBundle 'therubymug/vim-pyte'
NeoBundle 'tomasr/molokai'
NeoBundle 'digitaltoad/vim-jade'

call neobundle#end()

filetype plugin indent on     " required!


" If there are uninstalled bundles found on startup,
" this will conveniently prompt you to install them.
NeoBundleCheck

" -----------------------
" Fuf setting
" -----------------------

nnoremap <silent> <space>fb :FufBuffer!<CR>
nnoremap <silent> <space>ff :FufFile! <C-r>=expand('%:‾:.')[:-1-len(expand('%:‾:.:t'))]<CR><CR>
nnoremap <silent> <space>fd :FufDir! <C-r>=expand('%:p:‾')[:-1-len(expand('%:p:‾:t'))]<CR><CR>
nnoremap <silent> <space>fm :FufMruFile<CR>
nnoremap <silent> <Space>fc :FufRenewCache<CR>
autocmd FileType fuf nmap <C-c> <ESC>
let g:fuf_patternSeparator = ' '
let g:fuf_modesDisable = ['mrucmd']
let g:fuf_mrufile_exclude = '¥v¥.DS_Store|¥.git|¥.swp|¥.svn'
let g:fuf_mrufile_maxItem = 100
let g:fuf_enumeratingLimit = 20
let g:fuf_file_exclude = '¥v¥.DS_Store|¥.git|¥.swp|¥.svn'



" -----------------------
" zencoding setting
" -----------------------

"let g:user_zen_expandabbr_key = '<C-d>'



" -----------------------
" emmet setting
" -----------------------

let g:user_emmet_mode = 'i'
let g:user_emmet_leader_key='<C-D>'
let g:user_emmet_install_global = 0
autocmd FileType html,css,scss EmmetInstall



" -----------------------
" unite setting
" -----------------------

" Enable unite in insert mode
let g:unite_enable_start_insert=1
" Enable yank history
let g:unite_source_history_yank_enable=1
" Define limit of mru files
let g:unite_source_file_mru_limit=200
" Open yunk history
nnoremap <silent> <space>uy :<C-u>Unite history/yank<CR>
" Open buffer
nnoremap <silent> <space>ub :<C-u>Unite buffer<CR>
" Open same directory files
nnoremap <silent> <space>uf :<C-u>UniteWithBufferDir -buffer-name=files file<CR>
" Open register
nnoremap <silent> <space>ur :<C-u>Unite -buffer-name=register register<CR>
" Open most recent used file
nnoremap <silent> <space>uu :<C-u>Unite file_mru buffer<CR>



" -----------------------
" neocomplcache setting
" -----------------------

" Disable AutoComplPop.
let g:acp_enableAtStartup = 0

" Enable neocomplcache
let g:neocomplcache_enable_at_startup = 1

" Use smartcase.
let g:neocomplcache_enable_smart_case = 1

" Set minimum syntax keyword length.
let g:neocomplcache_min_syntax_length = 3

" Buffer file name pattern that locks neocomplcache. e.g. ku.vim or fuzzyfinder
let g:neocomplcache_lock_buffer_name_pattern = '¥*fuf¥*'

" Heavy features.
" Use camel case completion.
"let g:neocomplcache_enable_camel_case_completion = 1
"
" Use underscore completion.
"let g:neocomplcache_enable_underbar_completion = 1

" Define dictionary.
let g:neocomplcache_dictionary_filetype_lists = {
  \ 'default' : '',
  \ 'vimshell' : $HOME.'/.vimshell_hist',
  \ 'scheme' : $HOME.'/.gosh_completions'
\ }

" Define keyword.
if !exists('g:neocomplcache_keyword_patterns')
    let g:neocomplcache_keyword_patterns = {}
endif
let g:neocomplcache_keyword_patterns['default'] = '\h\w*'

" Plugin key-mappings.
inoremap <expr><C-g>     neocomplcache#undo_completion()
inoremap <expr><C-l>     neocomplcache#complete_common_string()

" SuperTab like snippets behavior.
imap <expr><TAB> neocomplcache#sources#snippets_complete#expandable() ? "\<Plug>(neocomplcache_snippets_expand)" : pumvisible() ? "\<C-n>" : "\<TAB>"
"smap <expr><TAB> neocomplcache#sources#snippets_complete#expandable() ? "\<Plug>(neocomplcache_snippets_expand)" : pumvisible() ? "\<C-n>" : "\<TAB>"

" Recommended key-mappings.
" <CR>: close popup and save indent.
inoremap <silent> <CR> <C-r>=<SID>my_cr_function()<CR>
function! s:my_cr_function()
  return neocomplcache#smart_close_popup() . "\<CR>"
  " For no inserting <CR> key.
  "return pumvisible() ? neocomplcache#close_popup() : "\<CR>"
endfunction
" <TAB>: completion.
" use SuperTab
" inoremap <expr><TAB>  pumvisible() ? "\<C-n>" : "\<TAB>"
" <C-h>, <BS>: close popup and delete backword char.
inoremap <expr><C-h> neocomplcache#smart_close_popup()."\<C-h>"
inoremap <expr><BS> neocomplcache#smart_close_popup()."\<C-h>"
inoremap <expr><C-y>  neocomplcache#close_popup()
inoremap <expr><C-e>  neocomplcache#cancel_popup()

" For cursor moving in insert mode(Not recommended)
"inoremap <expr><Left>  neocomplcache#close_popup() . "\<Left>"
"inoremap <expr><Right> neocomplcache#close_popup() . "\<Right>"
"inoremap <expr><Up>    neocomplcache#close_popup() . "\<Up>"
"inoremap <expr><Down>  neocomplcache#close_popup() . "\<Down>"

" AutoComplPop like behavior.
let g:neocomplcache_enable_auto_select = 1

" Enable omni completion.
autocmd FileType css,scss setlocal omnifunc=csscomplete#CompleteCSS
autocmd FileType html,markdown setlocal omnifunc=htmlcomplete#CompleteTags
autocmd FileType javascript,coffeescript,coffee setlocal omnifunc=javascriptcomplete#CompleteJS
autocmd FileType python setlocal omnifunc=pythoncomplete#Complete
autocmd FileType xml setlocal omnifunc=xmlcomplete#CompleteTags

" Enable heavy omni completion.
if !exists('g:neocomplcache_omni_patterns')
  let g:neocomplcache_omni_patterns = {}
endif
let g:neocomplcache_omni_patterns.ruby = '[^. *¥t]¥.¥h¥w*¥|¥h¥w*::'
let g:neocomplcache_omni_patterns.php = '[^. ¥t]->¥h¥w*¥|¥h¥w*::'
let g:neocomplcache_omni_patterns.c = '¥%(¥.¥|->¥)¥h¥w*'
let g:neocomplcache_omni_patterns.cpp = '¥h¥w*¥%(¥.¥|->¥)¥h¥w*¥|¥h¥w*::'



" -----------------------
" neosnippet setting
" -----------------------

" Plugin key-mappings.
imap <C-k>     <Plug>(neosnippet_expand_or_jump)
smap <C-k>     <Plug>(neosnippet_expand_or_jump)

" SuperTab like snippets behavior.
imap <expr><TAB> neosnippet#expandable_or_jumpable() ? "\<Plug>(neosnippet_expand_or_jump)" : pumvisible() ? "\<C-n>" : "\<TAB>"
smap <expr><TAB> neosnippet#expandable_or_jumpable() ? "\<Plug>(neosnippet_expand_or_jump)" : "\<TAB>"

" For snippet_complete marker.
if has('conceal')
  set conceallevel=2 concealcursor=i
endif

" Tell Neosnippet about the other snippets
"let g:neosnippet#snippets_directory=$VIMRUNTIME.'/snippets'




" -----------------------
" Enable jscomplete-vim
" -----------------------

autocmd FileType javascript setlocal omnifunc=jscomplete#CompleteJS
let g:jscomplete_use = ['dom']

" For snippet_complete marker.
if has('conceal')
  set conceallevel=2 concealcursor=i
endif




" -----------------------
" surround.vim setting
" -----------------------

" [key map]
autocmd FileType html let b:surround_49  = "<h1>\r</h1>"
autocmd FileType html let b:surround_50  = "<h2>\r</h2>"
autocmd FileType html let b:surround_51  = "<h3>\r</h3>"
autocmd FileType html let b:surround_52  = "<h4>\r</h4>"
autocmd FileType html let b:surround_53  = "<h5>\r</h5>"
autocmd FileType html let b:surround_54  = "<h6>\r</h6>"

autocmd FileType html let b:surround_112 = "<p>¥r</p>"
autocmd FileType html let b:surround_117 = "<ul>¥r</ul>"
autocmd FileType html let b:surround_111 = "<ol>¥r</ol>"
autocmd FileType html let b:surround_108 = "<li>¥r</li>"
autocmd FileType html let b:surround_97  = "<a href=\"\">\r</a>"
autocmd FileType html let b:surround_65  = "<a href=\"\r\"></a>"
autocmd FileType html let b:surround_105 = "<img src=\"\r\" alt=\"\">"
autocmd FileType html let b:surround_73  = "<img src=\"\" alt=\"\r\">"
autocmd FileType html let b:surround_100 = "<div>\r</div>"
autocmd FileType html let b:surround_68  = "<div class=\"section\">\r</div>"



" -----------------------
" vimsum
" -----------------------
nmap <Leader>sp "sp



" -----------------------
" vim-gitgutter
" -----------------------
let g:gitgutter_sign_added = '✚'
let g:gitgutter_sign_modified = '➜'
let g:gitgutter_sign_removed = '✘'



" -----------------------
" coffeescript settings
" -----------------------
" vimにcoffeeファイルタイプを認識させる
au BufRead,BufNewFile,BufReadPre *.coffee   set filetype=coffee
" インデントを設定
autocmd FileType coffee     setlocal sw=2 sts=2 ts=2 et



" -----------------------
" indent_guides
"------------------------
"" インデントの深さに色を付ける
let g:indent_guides_start_level=2
let g:indent_guides_auto_colors=1
let g:indent_guides_enable_on_vim_startup=0
let g:indent_guides_color_change_percent=20
let g:indent_guides_guide_size=2
let g:indent_guides_space_guides=1

hi IndentGuidesOdd  ctermbg=235
hi IndentGuidesEven ctermbg=237
au FileType coffee,coffeescript,ruby,javascript,python IndentGuidesEnable
nmap <silent><Leader>ig <Plug>IndentGuidesToggle



" -----------------------
" lightline
" -----------------------
let g:lightline = {
      \ 'colorscheme': 'wombat',
      \ 'mode_map': { 'c': 'NORMAL' },
      \ 'active': {
      \   'left': [ [ 'mode', 'paste' ], [ 'fugitive', 'filename' ] ]
      \ },
      \ 'component_function': {
      \   'modified': 'MyModified',
      \   'readonly': 'MyReadonly',
      \   'fugitive': 'MyFugitive',
      \   'filename': 'MyFilename',
      \   'fileformat': 'MyFileformat',
      \   'filetype': 'MyFiletype',
      \   'fileencoding': 'MyFileencoding',
      \   'mode': 'MyMode',
      \ },
      \ 'separator': { 'left': '⮀', 'right': '⮂' },
      \ 'subseparator': { 'left': '⮁', 'right': '⮃' }
      \ }

function! MyModified()
  return &ft =~ 'help\|vimfiler\|gundo' ? '' : &modified ? '+' : &modifiable ? '' : '-'
endfunction

function! MyReadonly()
  return &ft !~? 'help\|vimfiler\|gundo' && &readonly ? '⭤' : ''
endfunction

function! MyFilename()
  return ('' != MyReadonly() ? MyReadonly() . ' ' : '') .
        \ (&ft == 'vimfiler' ? vimfiler#get_status_string() :
        \  &ft == 'unite' ? unite#get_status_string() :
        \  &ft == 'vimshell' ? vimshell#get_status_string() :
        \ '' != expand('%:t') ? expand('%:t') : '[No Name]') .
        \ ('' != MyModified() ? ' ' . MyModified() : '')
endfunction

function! MyFugitive()
  if &ft !~? 'vimfiler\|gundo' && exists("*fugitive#head")
    let _ = fugitive#head()
    return strlen(_) ? '⭠ '._ : ''
  endif
  return ''
endfunction

function! MyFileformat()
  return winwidth(0) > 70 ? &fileformat : ''
endfunction

function! MyFiletype()
  return winwidth(0) > 70 ? (strlen(&filetype) ? &filetype : 'no ft') : ''
endfunction

function! MyFileencoding()
  return winwidth(0) > 70 ? (strlen(&fenc) ? &fenc : &enc) : ''
endfunction

function! MyMode()
  return winwidth(0) > 60 ? lightline#mode() : ''
endfunction



" -----------------------
" vim-easymotion
" -----------------------
let g:EasyMotion_do_mapping = 0 " Disable default mappings

" Bi-directional find motion
" Jump to anywhere you want with minimal keystrokes, with just one key binding.
" `s{char}{label}`
nmap s <Plug>(easymotion-s)
" or
" `s{char}{char}{label}`
" Need one more keystroke, but on average, it may be more comfortable.
nmap s <Plug>(easymotion-s2)

" Turn on case sensitive feature
let g:EasyMotion_smartcase = 1

" JK motions: Line motions
map <Leader>j <Plug>(easymotion-j)

map f <Plug>(easymotion-bd-fl)
map t <Plug>(easymotion-bd-tl)

" Gif config
nmap s <Plug>(easymotion-s2)
nmap t <Plug>(easymotion-t2)
" surround.vimと被らないように
omap z <Plug>(easymotion-s2)

" Gif config
map  / <Plug>(easymotion-sn)
omap / <Plug>(easymotion-tn)

" These `n` & `N` mappings are options. You do not have to map `n` & `N` to EasyMotion.
" Without these mappings, `n` & `N` works fine. (These mappings just provide
" different highlight method and have some other features )
map  n <Plug>(easymotion-next)




" -----------------------
" vim-easymotion
" -----------------------
let g:EasyMotion_do_mapping = 0 " Disable default mappings

" Jump to first match with enter & space
let g:EasyMotion_enter_jump_first = 1
let g:EasyMotion_space_jump_first = 1

" Bi-directional find motion
" Jump to anywhere you want with minimal keystrokes, with just one key binding.
" `s{char}{label}`
nmap s <Plug>(easymotion-s)
" or
" `s{char}{char}{label}`
" Need one more keystroke, but on average, it may be more comfortable.
nmap s <Plug>(easymotion-s2)
xmap s <Plug>(easymotion-s2)
" surround.vimと被らないように
omap z <Plug>(easymotion-s2)

" Turn on case sensitive feature
let g:EasyMotion_smartcase = 1

" JK motions: Line motions
map <Leader>j <Plug>(easymotion-j)
map <Leader>k <Plug>(easymotion-k)

map f <Plug>(easymotion-bd-fl)
map t <Plug>(easymotion-bd-tl)

" =======================================
" Search Motions
" =======================================
" Extend search motions with vital-over command line interface
" Incremental highlight of all the matches
" Now, you don't need to repetitively press `n` or `N` with EasyMotion feature
" `<Tab>` & `<S-Tab>` to scroll up/down a page of next match
" :h easymotion-command-line
nmap g/ <Plug>(easymotion-sn)
xmap g/ <Plug>(easymotion-sn)
omap g/ <Plug>(easymotion-tn)
" Support mappings feature
"EMCommandLineNoreMap <Space> <CR>
"EMCommandLineNoreMap ; <CR>
"EMCommandLineNoreMap <C-j> <Space>


" -----------------------
" vimgrepで自動的にQuickFixを開く
" -----------------------
au QuickFixCmdPost vimgrep cw



" -----------------------
" end setup
" -----------------------
set laststatus=2
if !has('gui_running')
  set t_Co=256
endif
set ambiwidth=double
