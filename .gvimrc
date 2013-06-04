"---------------------------------------------------------------------------
" フォント設定:
"
if has('win32')
  " Windows用
  "set guifont=Hiragino\ Kaku\ Gothic\ Pro\ W4:h11:cUTF-8
  set guifont=MS_Gothic:h11:cDEFAULT
  "set guifont=MS_Mincho:h12:cSHIFTJIS
  " 行間隔の設定
  set linespace=1
  " 一部のUCS文字の幅を自動計測して決める
  if has('kaoriya')
    set ambiwidth=auto
  endif
elseif has('mac')
  set guifont=Osaka－等幅:h14
elseif has('xfontset')
  " UNIX用 (xfontsetを使用)
  set guifontset=a14,r14,k14
endif

"---------------------------------------------------------------------------
" ウインドウに関する設定:
"
" ウインドウの幅
set columns=200
" ウインドウの高さ
set lines=55
" コマンドラインの高さ(GUI使用時)
set cmdheight=2

" ルーラーを表示 (noruler:非表示)
set ruler

"ウィンドウを最大化
if has("gui_running")
  if has('mac')
    set fuoptions=maxvert,maxhorz
    au GUIEnter * set fullscreen
  elseif has('win32')
    au GUIEnter * simalt ~X
  endif
endif

"-------------------------------------------------------------------------------
" デザイン
" アンチエイリアシング
set antialias

" カラースキーマの設定
colorscheme wombat

" wombatのVisualモードをdesert風(緑っぽいやつ)にする
if g:colors_name ==? 'wombat'
  hi Visual gui=none guifg=khaki guibg=olivedrab
endif

"---------------------------------------------------------------------------
" ウィンドウ作成後

gui
" 半透明
set transparency=230


