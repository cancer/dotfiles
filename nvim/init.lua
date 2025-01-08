vim.opt.number = true
vim.opt.tabstop = 2
vim.opt.shiftwidth = 2
vim.opt.expandtab = true
vim.opt.smartcase = true
vim.opt.clipboard:append {'unnamedplus'}

vim.lsp.set_log_level("debug")

-- Key mappings
vim.keymap.set('n', '<C-1>', ':NvimTreeToggle<CR>', { noremap = true, silent = true })
vim.keymap.set('n', '<C-k>', vim.lsp.buf.hover, { noremap = true, silent = true })
vim.keymap.set('n', '<C-[>', ':tabnext<CR>', { noremap = true, silent = true })
vim.keymap.set("n", "<F2>", vim.lsp.buf.rename, { noremap = true, silent = true })
vim.keymap.set('n', '<C-p>', ':Telescope find_files<CR>', { noremap = true, silent = true })
vim.keymap.set('n', '<F12>', ':Telescope lsp_document_symbols<CR>', { noremap = true, silent = true })

-- Install plugin manager
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.loop.fs_stat(lazypath) then
  vim.fn.system({
    "git", "clone", "--filter=blob:none",
    "https://github.com/folke/lazy.nvim.git",
    "--branch=stable",
    lazypath,
  })
end
vim.opt.rtp:prepend(lazypath)

-- Setup plugins
require("lazy").setup({
  -- LSP
  {
    "neovim/nvim-lspconfig",
    config = function()
      local lspconfig = require("lspconfig")

      -- Astro LSP 設定
      lspconfig.astro.setup({
        root_dir = require("lspconfig.util").root_pattern("package.json", ".git"),
        on_attach = function(client, bufnr)
          vim.keymap.set("n", "<F2>", vim.lsp.buf.rename, { noremap = true, silent = true, buffer = bufnr })
        end,
      })

      -- TypeScript LSP 設定
      lspconfig.ts_ls.setup({
        root_dir = require("lspconfig.util").root_pattern("package.json", "tsconfig.json", ".git"),
        on_attach = function(client, bufnr)
          vim.keymap.set("n", "<F2>", vim.lsp.buf.rename, { noremap = true, silent = true, buffer = bufnr })
        end,
      })
    end,
  },
  {
    "jinzhongjia/LspUI.nvim",
    branch = "main",
    config = function()
      require("LspUI").setup({
        hover = { enable = true }
      })
    end
  },
  -- Formatter
  {
    "prettier/vim-prettier",
    build = "npm install",
    ft = { "javascript", "typescript", "css", "json", "markdown", "astro", "svelte" },
    cmd = { "Prettier", "PrettierAsync" },
    config = function()
    end,
  },
  -- Auto complete
  {
    "hrsh7th/nvim-cmp",
    dependencies = {
      "hrsh7th/cmp-nvim-lsp",
      "hrsh7th/cmp-buffer",
      "hrsh7th/cmp-path",
      "L3MON4D3/LuaSnip"
    },
    config = function()
      local cmp = require("cmp")
      cmp.setup({
        snippet = {
          expand = function(args)
            require("luasnip").lsp_expand(args.body)
          end,
        },
        mapping = {
          ["<Tab>"] = cmp.mapping.select_next_item({ behavior = cmp.SelectBehavior.Insert }),
          ["<S-Tab>"] = cmp.mapping.select_prev_item({ behavior = cmp.SelectBehavior.Insert }),
          ["<CR>"] = cmp.mapping.confirm({ select = true }),
        },
        sources = {
          { name = "nvim_lsp" },
          { name = "buffer" },
          { name = "path" },
        },
      })
    end,
  },
  -- Syntax highlighter
  {
    "nvim-treesitter/nvim-treesitter",
    build = ":TSUpdate",
    config = function()
      require("nvim-treesitter.configs").setup({
        ensure_installed = { "javascript", "typescript", "html", "css", "json", "astro", "svelte", "markdown" },
        highlight = { enable = true },
        indent = { enable = true },
        auto_install = true,
      })
    end,
  },
  -- Search
  {
    "nvim-telescope/telescope.nvim",
    dependencies = { "nvim-lua/plenary.nvim" },
    config = function()
      require("telescope").setup({})
    end,
  },
  -- Git
  {
    "lewis6991/gitsigns.nvim",
    config = true,
  },
  -- Status line
  {
    "nvim-lualine/lualine.nvim",
    dependencies = { "nvim-tree/nvim-web-devicons" },
    config = function()
      require("lualine").setup()
    end,
  },
  -- Filetree
  {
    "nvim-tree/nvim-tree.lua",
    dependencies = { "nvim-tree/nvim-web-devicons" },
    config = function()
      require("nvim-tree").setup({
        update_focused_file = {
          enable = true
        },
        on_attach = function(bufnr)
          local api = require('nvim-tree.api')
          local function opts(desc)
            return { desc = 'nvim-tree: ' .. desc, buffer = bufnr, noremap = true, silent = true, nowait = true }
          end
          api.config.mappings.default_on_attach(bufnr)

          -- Remap
          vim.keymap.set('n', '<CR>', function()
            api.node.open.tab()
            api.tree.open()
          end, opts('Open: New Tab'))
        end,
      })

      -- Launch
      local nvim_tree = require("nvim-tree.api")
      vim.api.nvim_create_autocmd("VimEnter", {
        callback = function()
          nvim_tree.tree.open()
        end
      });
    end,
  },
  {
    "antosha417/nvim-lsp-file-operations",
    dependencies = {
      'nvim-lua/plenary.nvim',
      "nvim-tree/nvim-tree.lua",
    },
    config = function()
      require("lsp-file-operations").setup({
        debug = true
      })
    end,
  },
  {
    'projekt0n/github-nvim-theme',
    name = 'github-theme',
    lazy = false,
    priority = 1000,
    config = function()
      require('github-theme').setup()

      vim.cmd('colorscheme github_dark_colorblind')
    end,
  }
})

