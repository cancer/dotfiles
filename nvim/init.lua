vim.opt.number = true
vim.opt.tabstop = 2
vim.opt.shiftwidth = 2
vim.opt.expandtab = true
vim.opt.smartcase = true
vim.opt.clipboard:append {'unnamedplus'}

vim.g.mapleader = " "

-- Key mappings
vim.keymap.set('n', '<C-1>', ':NvimTreeToggle<CR>', { noremap = true, silent = true })
vim.keymap.set('n', '<C-k>', vim.lsp.buf.hover, { noremap = true, silent = true })
vim.keymap.set('n', '<C-[>', ':tabnext<CR>', { noremap = true, silent = true })
vim.keymap.set('n', '<C-S-[>', ':tabprev<CR>', { noremap = true, silent = true })
vim.keymap.set("n", "<F2>", vim.lsp.buf.rename, { noremap = true, silent = true })
vim.keymap.set('n', '<C-p>', ':Telescope<CR>', { noremap = true, silent = true })
vim.keymap.set('n', '<leader>pf', ':Telescope find_files<CR>', { noremap = true, silent = true })
vim.keymap.set('n', '<leader>ps', ':Telescope lsp_document_symbols<CR>', { noremap = true, silent = true })
vim.keymap.set('n', '<leader>P', ':Neoformat<CR>', { noremap = true, silent = true })

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
      -- キーマップ + positionEncoding は LspAttach で全アタッチに適用する。
      -- vim.lsp.config("*", {on_attach=...}) はサーバ独自の on_attach（svelte/ts_ls）に
      -- マージで置換され消えるため、autocmd 方式で共存させる。
      vim.api.nvim_create_autocmd("LspAttach", {
        callback = function(args)
          local bufnr = args.buf
          local client = vim.lsp.get_client_by_id(args.data.client_id)
          if client then
            client.server_capabilities.positionEncoding = "utf-16"
          end

          vim.keymap.set("n", "<F2>", vim.lsp.buf.rename, { noremap = true, silent = true, buffer = bufnr })
          vim.keymap.set("n", "<C-CR>", vim.lsp.buf.code_action, { noremap = true, silent = true, buffer = bufnr })
          vim.keymap.set("n", "<leader>gd", vim.lsp.buf.definition, { noremap = true, silent = true, buffer = bufnr })
          vim.keymap.set("n", "<leader>gi", vim.lsp.buf.implementation, { noremap = true, silent = true, buffer = bufnr })
          vim.keymap.set("n", "<leader>gD", vim.lsp.buf.declaration, { noremap = true, silent = true, buffer = bufnr })
          vim.keymap.set("n", "<leader>gr", vim.lsp.buf.references, { noremap = true, silent = true, buffer = bufnr })
          vim.keymap.set("n", "<leader>tD", vim.lsp.buf.type_definition, { noremap = true, silent = true, buffer = bufnr })
          vim.keymap.set("n", "K", vim.lsp.buf.hover, { noremap = true, silent = true, buffer = bufnr })
        end,
      })

      -- ts_ls のみ init_options を上書き
      -- cmd / filetypes / root は nvim-lspconfig 内蔵の lsp/*.lua の既定を使用する
      vim.lsp.config("ts_ls", {
        init_options = {
          hostInfo = "neovim",
          preferences = {
            enableSuggestions = true,
            includeCompletionsForModuleExports = true,
            includeCompletionsForImportStatements = true,
            includePackageJsonAutoImports = "on",
            importModuleSpecifierPreference = "project-relative",
          },
        },
      })

      vim.lsp.enable({ "astro", "svelte", "ts_ls" })
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

  -- Finder
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
        filters = {
          git_ignored = false,
          custom = { "^\\.git$", "^\\.idea$", "^\\.vscode$", "^\\.DS_Store$" },
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
    branch = "main",
    build = ":TSUpdate",
    config = function()
      local langs = { "javascript", "typescript", "html", "css", "json", "astro", "svelte", "markdown" }
      require("nvim-treesitter").install(langs)
      vim.api.nvim_create_autocmd("FileType", {
        pattern = langs,
        callback = function()
          pcall(vim.treesitter.start)
          vim.bo.indentexpr = "v:lua.require'nvim-treesitter'.indentexpr()"
        end,
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
      lint.linters.eslint.cmd = function()
        local cwd = vim.fn.getcwd()
        local local_eslint = cwd .. '/node_modules/.bin/eslint'
        if vim.fn.executable(local_eslint) == 1 then
          return local_eslint
        else
          return 'eslint' -- fallback
        end
      end

      -- vim.api.nvim_create_autocmd({ "BufWritePost" }, {
      --   callback = function()
      --     lint.try_lint()
      --   end,
      -- })
      -- vim.api.nvim_create_autocmd({ "BufReadPost" }, {
      --   callback = function()
      --     lint.try_lint()
      --   end,
      -- })

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
    "sbdchd/neoformat",
    config = function()
      vim.env.PATH = vim.fn.expand("~/dotfiles/node_modules/.bin") .. ":" .. vim.env.PATH
    end,
  },

  {
    "cajames/copy-reference.nvim",
    keys = {
      { "yr", "<cmd>CopyReference<cr>", mode = { "n", "v" }, desc = "Copy file reference with line number" },
    },
    config = true,
  },
  {
    "coder/claudecode.nvim",
    opts = { terminal_cmd = "claude --permission-mode auto" },
    keys = {
      { "<leader>ac", "<cmd>ClaudeCode<cr>", desc = "Claude: Chat" },
      { "<leader>ab", "<cmd>ClaudeCodeAdd %<cr>", desc = "Add current buffer" },
      { "<leader>as", "<cmd>ClaudeCodeSend<cr>", mode = "v", desc = "Claude: Send selection" },
      { "<leader>ar", "<cmd>ClaudeCode --resume<cr>", desc = "Resume Claude" },
      { "<leader>aw", "<cmd>ClaudeCode -w<cr>", desc = "Claude: Worktree" },
    }
  },
  {
    "ishiooon/codex.nvim",
    dependencies = { "folke/snacks.nvim" },
    config = true,
    keys = {
      { "<leader>cc", "<cmd>Codex<cr>", desc = "Codex: Toggle" },
      { "<leader>cf", "<cmd>CodexFocus<cr>", desc = "Codex: Focus" },
      { "<leader>cm", "<cmd>CodexMaximizeToggle<cr>", desc = "Codex: Toggle modal" },
      { "<leader>cs", "<cmd>CodexSend<cr>", mode = "v", desc = "Codex: Send selection" },
    },
  },
  {
    "NakLast/antigravity-cli.nvim",
    config = function()
      require("antigravity").setup({})
    end,
    keys = {
      { "<leader>gc", "<cmd>Antigravity<cr>", desc = "Antigravity: Toggle" },
    },
  }
})

-- Dim inactive windows in tmux
local augroup = vim.api.nvim_create_augroup("TmuxFocus", { clear = true })

if os.getenv("TMUX") then
  vim.api.nvim_create_autocmd("FocusGained", {
    group = augroup,
    pattern = "*",
    callback = function()
      vim.cmd("hi Normal ctermbg=NONE guibg=NONE")
      vim.cmd("hi NormalNC ctermbg=NONE guibg=NONE")
    end,
  })
  vim.api.nvim_create_autocmd("FocusLost", {
    group = augroup,
    pattern = "*",
    callback = function()
      vim.cmd("hi Normal ctermbg=236 guibg=#202020")
      vim.cmd("hi NormalNC ctermbg=236 guibg=#202020")
    end,
  })
end

