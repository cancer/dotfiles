"---------------------------------------------------------------------------
" 環境設定


" -----------------------
" vimproc にpathを通す
" -----------------------

if has('win64')
  let g:vimproc_dll_path = $VIM . '/runtime/bundle/vimproc/autoload/vimproc_win64.dll'
endif



" -----------------------
" _vimrcを良い感じに開く
" -----------------------

let s:vimrcbody = '$VIM/_vimrc'
let s:gvimrcbody = '$VIM/_gvimrc'
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
nnoremap ,, :<C-u>OpenMyVimrc<CR>
nnoremap ,<Tab> :<C-u>OpenMyGVimrc<CR>


" -----------------------
" F5でリロード
" -----------------------

function! SourceIfExists(file)
  if filereadable(expand(a:file))
    execute 'source ' . a:file
  endif
  echo 'Reloaded vimrc and gvimrc and ' . a:file . '.'
  FullScreen
endfunction
nnoremap <F5> <Esc>:<C-u>source $MYVIMRC<CR> :source $MYGVIMRC<CR> :call SourceIfExists($FTPLUGIN .'¥'. &filetype . '.vim')<CR>

" Map double-tap Esc to clear search highlights
nnoremap <silent> <Esc><Esc> <Esc>:nohlsearch<CR><Esc>



"---------------------------------------------------------------------------
" プラグイン管理

" -----------------------
" NeoBundleの読み込み/設定
" -----------------------

set nocompatible
filetype off

let $PATH = $PATH . ';C:¥WorkSpace¥tools¥MinGW¥bin;C:¥WorkSpace¥tools¥MinGW¥msys¥1.0¥bin;C:¥Git¥cmd;C:¥Git¥bin'

if has('vim_starting')
  set runtimepath+=$VIMRUNTIME/bundle/neobundle.vim/
endif

call neobundle#rc(expand('$VIMRUNTIME/bundle/'))

" originalrepos on github
NeoBundle 'Shougo/neobundle.vim'
NeoBundle 'Shougo/vimproc'
NeoBundle 'Shougo/unite.vim.git'
NeoBundle 'Shougo/neocomplcache'
NeoBundle 'Shougo/neosnippet'
NeoBundle 'Shougo/vimshell'
NeoBundle 'Shougo/vimfiler.vim'
NeoBundle 'mattn/zencoding-vim'
NeoBundle 'ujihisa/vimshell-ssh'
NeoBundle 'nathanaelkane/vim-indent-guides'

" vim-scripts repos
NeoBundle 'L9'
NeoBundle 'FuzzyFinder'
NeoBundle 'surround.vim'
NeoBundle 'visSum.vim'

filetype plugin indent on     " required!



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
set tabstop=4

" -----------------------
" タブ幅
" -----------------------
set softtabstop=4

" -----------------------
" タブを挿入するときの幅
" -----------------------
set shiftwidth=4

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
set listchars=tab:>-,extends:<,trail:-,eol:$

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

"---------------------------------------------------------------------------
" ファイル操作に関する設定:

" -----------------------
" バックアップファイルを作成しない (次行の先頭の " を削除すれば有効になる)
" -----------------------
set nobackup

" ---------------------------------------------------------------------------
" 編集関連

" -----------------------
"クリップボードをOSと連携
" -----------------------

if has('win32')
  set clipboard=unnamed
else
  set clipboard=unnamed,autoselect
endif



" -----------------------
"カーソルを行頭、行末で止まらないようにする
" -----------------------
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




" -----------------------
" ステータスラインに文字コードと改行文字を表示する
" -----------------------
"
" set statusline=%<%f¥ %m%r%h%w%{'['.(&fenc!=''?&fenc:&enc).']['.&ff.']'}%=%l,%c%V%8P
set statusline=%{expand('%:p:t')}¥ %<¥(%{SnipMid(expand('%:p:h'),80-len(expand('%:p:t')),'...')}¥)%=¥ %m%r%y%w%{'['.(&fenc!=''?&fenc:&enc).']['.&ff.']'}[%3l,%3c]%8P




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

"---------------------------------------------------------------------------
" ファイル設定関連

" -----------------------
" fileencode を設定
" -----------------------

set fileencodings=utf-8,euc-jp,sjis,cp932

au BufNewFile,BufRead *.md setfiletype markdown

" -----------------------
" vimshellエンコーディングエラー対策
" -----------------------
"Windows7ターミナル内はsjisなので

set termencoding=sjis

syntax on


"---------------------------------------------------------------------------
" キーマップ設定 
nnoremap ZZ <Nop>

nnoremap j gj
nnoremap k gk
nnoremap gj j
nnoremap gk k
nnoremap <C-Up> 5k
nnoremap <C-Down> 5j
noremap <C-k> 5k
noremap <C-j> 5j


inoremap <C-z> <Esc>

" open new tab
nnoremap <c-n> :<c-u>tabnew<cr>

" change buffer
nnoremap gb :<C-u>bn<CR>
nnoremap gB :<C-u>bp<CR>
nnoremap cb :<C-u>bd<CR>

" VimShell
" シェルを起動
nnoremap <silent> ,vs :VimShell<CR>



" ---------------------------------------------------------------------------
" プラグイン個別設定

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


" zencoding setting 
let g:user_zen_expandabbr_key = '<C-d>'
let g:user_zen_settings = {
¥  'html' : {
¥    'snippets' : {
¥     'img:sp' : "<img src=¥"[%url img=¥"#SPACE#¥"%]¥" alt=¥"¥" width=¥"1¥" height=¥"|¥" style=¥"border:none;¥" />",
¥    },
¥  },
¥}


" -----------------------
" neocomplcache setting 
" -----------------------

" Disable AutoComplPop.
let g:acp_enableAtStartup = 0

" enable neocomplcache
let g:neocomplcache_enable_at_startup = 1

" Use smartcase.
let g:neocomplcache_enable_smart_case = 1

" Use camel case completion.
let g:neocomplcache_enable_camel_case_completion = 1
"
" Use underscore completion.
let g:neocomplcache_enable_underbar_completion = 1

" Set minimum syntax keyword length.
let g:neocomplcache_min_syntax_length = 3

" buffer file name pattern that locks neocomplcache. e.g. ku.vim or fuzzyfinder 
let g:neocomplcache_lock_buffer_name_pattern = '¥*fuf¥*'

" Plugin key-mappings.
inoremap <expr><C-g>     neocomplcache#undo_completion()
inoremap <expr><C-l>     neocomplcache#complete_common_string()

" SuperTab like snippets behavior.
imap <expr><TAB> neocomplcache#sources#snippets_complete#expandable() ? "¥<Plug>(neocomplcache_snippets_expand)" : pumvisible() ? "¥<C-n>" : "¥<TAB>"
"smap <expr><TAB> neocomplcache#sources#snippets_complete#expandable() ? "¥<Plug>(neocomplcache_snippets_expand)" : pumvisible() ? "¥<C-n>" : "¥<TAB>"

" Recommended key-mappings.
" <CR>: close popup and save indent.
inoremap <expr><CR>  neocomplcache#close_popup() . "¥<CR>"

" <C-h>, <BS>: close popup and delete backword char.
inoremap <expr><C-h> neocomplcache#smart_close_popup()."¥<C-h>"
inoremap <expr><BS> neocomplcache#smart_close_popup()."¥<C-h>"
inoremap <expr><C-y>  neocomplcache#close_popup()
inoremap <expr><C-e>  neocomplcache#cancel_popup()

" For cursor moving in insert mode(Not recommended)
inoremap <expr><Left>  neocomplcache#close_popup() . "¥<Left>"
inoremap <expr><Right> neocomplcache#close_popup() . "¥<Right>"
inoremap <expr><Up>    neocomplcache#close_popup() . "¥<Up>"
inoremap <expr><Down>  neocomplcache#close_popup() . "¥<Down>"

" AutoComplPop like behavior.
let g:neocomplcache_enable_auto_select = 1

" Enable omni completion.
autocmd FileType css,scss setlocal omnifunc=csscomplete#CompleteCSS
autocmd FileType html,markdown setlocal omnifunc=htmlcomplete#CompleteTags
autocmd FileType javascript setlocal omnifunc=javascriptcomplete#CompleteJS
autocmd FileType python setlocal omnifunc=pythoncomplete#Complete
autocmd FileType xml setlocal omnifunc=xmlcomplete#CompleteTags

" Enable heavy omni completion.
if !exists('g:neocomplcache_omni_patterns')
  let g:neocomplcache_omni_patterns = {}
endif
let g:neocomplcache_omni_patterns.ruby = '[^. *¥t]¥.¥h¥w*¥|¥h¥w*::'
"autocmd FileType ruby setlocal omnifunc=rubycomplete#Complete
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
imap <expr><TAB> neosnippet#expandable_or_jumpable() ? "¥<Plug>(neosnippet_expand_or_jump)" : pumvisible() ? "¥<C-n>" : "¥<TAB>"
smap <expr><TAB> neosnippet#expandable_or_jumpable() ? "¥<Plug>(neosnippet_expand_or_jump)" : "¥<TAB>"

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
" for surround.vim
" -----------------------

" [key map]
autocmd FileType html let b:surround_49  = "<h1>¥r</h1>"
autocmd FileType html let b:surround_50  = "<h2>¥r</h2>"
autocmd FileType html let b:surround_51  = "<h3>¥r</h3>"
autocmd FileType html let b:surround_52  = "<h4>¥r</h4>"
autocmd FileType html let b:surround_53  = "<h5>¥r</h5>"
autocmd FileType html let b:surround_54  = "<h6>¥r</h6>"

autocmd FileType html let b:surround_112 = "<p>¥r</p>"
autocmd FileType html let b:surround_117 = "<ul>¥r</ul>"
autocmd FileType html let b:surround_111 = "<ol>¥r</ol>"
autocmd FileType html let b:surround_108 = "<li>¥r</li>"
autocmd FileType html let b:surround_97  = "<a href=¥"¥">¥r</a>"
autocmd FileType html let b:surround_65  = "<a href=¥"¥r¥"></a>"
autocmd FileType html let b:surround_105 = "<img src=¥"¥r¥" alt=¥"¥">"
autocmd FileType html let b:surround_73  = "<img src=¥"¥" alt=¥"¥r¥">"
autocmd FileType html let b:surround_100 = "<div>¥r</div>"
autocmd FileType html let b:surround_68  = "<div class=¥"section¥">¥r</div>"




" -----------------------
" vimsum
" -----------------------
nmap <Leader>sp "sp



" -----------------------
" vimgrepで自動的にQuickFixを開く
" -----------------------
au QuickFixCmdPost vimgrep cw







"
