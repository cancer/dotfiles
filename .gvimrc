"---------------------------------------------------------------------------
" �t�H���g�ݒ�:
"
if has('win32')
  " Windows�p
  "set guifont=Hiragino\ Kaku\ Gothic\ Pro\ W4:h11:cUTF-8
  set guifont=MS_Gothic:h11:cDEFAULT
  "set guifont=MS_Mincho:h12:cSHIFTJIS
  " �s�Ԋu�̐ݒ�
  set linespace=1
  " �ꕔ��UCS�����̕��������v�����Č��߂�
  if has('kaoriya')
    set ambiwidth=auto
  endif
elseif has('mac')
  set guifont=Osaka�|����:h14
elseif has('xfontset')
  " UNIX�p (xfontset���g�p)
  set guifontset=a14,r14,k14
endif

"---------------------------------------------------------------------------
" �E�C���h�E�Ɋւ���ݒ�:
"
" �E�C���h�E�̕�
set columns=200
" �E�C���h�E�̍���
set lines=55
" �R�}���h���C���̍���(GUI�g�p��)
set cmdheight=2

" ���[���[��\�� (noruler:��\��)
set ruler

"�E�B���h�E���ő剻
if has("gui_running")
  if has('mac')
    set fuoptions=maxvert,maxhorz
    au GUIEnter * set fullscreen
  elseif has('win32')
    au GUIEnter * simalt ~X
  endif
endif

"-------------------------------------------------------------------------------
" �f�U�C��
" �A���`�G�C���A�V���O
set antialias

" �J���[�X�L�[�}�̐ݒ�
colorscheme wombat

" wombat��Visual���[�h��desert��(�΂��ۂ����)�ɂ���
if g:colors_name ==? 'wombat'
  hi Visual gui=none guifg=khaki guibg=olivedrab
endif

"---------------------------------------------------------------------------
" �E�B���h�E�쐬��

gui
" ������
set transparency=230


