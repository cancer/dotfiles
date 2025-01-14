vim.opt.number = true
vim.opt.tabstop = 2
vim.opt.shiftwidth = 2
vim.opt.expandtab = true
vim.opt.smartcase = true
vim.opt.clipboard:append {'unnamedplus'}

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
      local on_attach = function(client, bufnr)
        vim.keymap.set("n", "<F2>", vim.lsp.buf.rename, { noremap = true, silent = true, buffer = bufnr })
        vim.keymap.set("n", "<F7>", vim.lsp.buf.references, { noremap = true, silent = true, buffer = bufnr })
        vim.keymap.set("n", "<C-CR>", vim.lsp.buf.code_action, { noremap = true, silent = true, buffer = bufnr })
      end

      lspconfig.astro.setup({
        root_dir = require("lspconfig.util").root_pattern("package.json", ".git"),
        on_attach = on_attach,
      })

      lspconfig.ts_ls.setup({
        root_dir = require("lspconfig.util").root_pattern("package.json", "tsconfig.json", ".git"),
        on_attach = on_attach,
        init_options = {
          hostInfo = "neovim",
          preferences = {
            includeCompletionForModuleExports = true,
            includeCompletionForImportStatements = true,
            importModuleSpecifierPreference = "project-relative"
          }
        }
      })
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

  -- Filetree
  {
    "nvim-tree/nvim-tree.lua",
    dependencies = { "nvim-tree/nvim-web-devicons" },
    config = function()
      require("nvim-tree").setup({
        update_focused_file = {
          enable = true
        },
      })
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

  -- Presentation
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
  {
    'projekt0n/github-nvim-theme',
    name = 'github-theme',
    lazy = false,
    priority = 1000,
    config = function()
      require('github-theme').setup()

      vim.cmd('colorscheme github_dark_colorblind')
    end,
  },

  -- UI
  {
    "nvim-lualine/lualine.nvim",
    dependencies = { "nvim-tree/nvim-web-devicons" },
    config = function()
      require("lualine").setup()
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

  -- Linter
    {
    "mfussenegger/nvim-lint",
    event = { "BufReadPre", "BufNewFile" },
    config = function()
      local lint = require("lint")
      vim.api.nvim_create_autocmd({ "BufWritePost" }, {
        callback = function()
          lint.try_lint()
        end,
      })
      vim.api.nvim_create_autocmd({ "BufReadPost" }, {
        callback = function()
          lint.try_lint()
        end,
      })

      lint.linters.eslint.cmd = function()
        local cwd = vim.fn.getcwd()
        local local_eslint = cwd .. '/node_modules/.bin/eslint'
        if vim.fn.executable(local_eslint) == 1 then
          return local_eslint
        else
          return 'eslint' -- fallback
        end
      end

      lint.linters_by_ft = {
        javascript = { 'eslint' },
        typescript = { 'eslint' },
        astro = { 'eslint' },
        svelte = { 'eslint' },
      }
    end,
  },

  -- Formatter
  {
    "prettier/vim-prettier",
    build = "npm install",
    ft = { "javascript", "typescript", "css", "json", "markdown", "astro", "svelte" },
    cmd = { "Prettier", "PrettierAsync" },
    config = function()
    end,
  }
})

