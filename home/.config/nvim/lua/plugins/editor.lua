return {
    {
        "nvim-treesitter/nvim-treesitter",
        branch = "main",
        lazy = false,
        build = ":TSUpdate",
        config = function()
            require("nvim-treesitter").install({
                "bash", "c", "cpp", "css", "go", "html", "javascript", "json", "lua",
                "markdown", "markdown_inline", "python", "query", "regex", "rust",
                "toml", "typescript", "vim", "vimdoc", "yaml",
            })
            vim.api.nvim_create_autocmd("FileType", {
                callback = function(ev)
                    if pcall(vim.treesitter.start, ev.buf) then
                        vim.bo[ev.buf].indentexpr = "v:lua.require'nvim-treesitter'.indentexpr()"
                    end
                end,
            })
        end,
    },
    {
        "nvim-tree/nvim-tree.lua",
        cmd = { "NvimTreeToggle", "NvimTreeFindFile" },
        keys = { { "<leader>e", "<cmd>NvimTreeToggle<cr>", desc = "File tree" } },
        dependencies = "nvim-tree/nvim-web-devicons",
        opts = {
            view = { width = 32 },
            renderer = { group_empty = true, indent_markers = { enable = true } },
            filters = { dotfiles = false },
            git = { ignore = false },
        },
    },
    {
        "nvim-telescope/telescope.nvim",
        cmd = "Telescope",
        dependencies = {
            "nvim-lua/plenary.nvim",
            { "nvim-telescope/telescope-fzf-native.nvim", build = "make" },
        },
        keys = {
            { "<leader>ff", "<cmd>Telescope find_files<cr>", desc = "Find files" },
            { "<leader>fg", "<cmd>Telescope live_grep<cr>", desc = "Grep" },
            { "<leader>fb", "<cmd>Telescope buffers<cr>", desc = "Buffers" },
            { "<leader>fh", "<cmd>Telescope help_tags<cr>", desc = "Help" },
            { "<leader>fr", "<cmd>Telescope oldfiles<cr>", desc = "Recent" },
            { "<leader>fd", "<cmd>Telescope diagnostics<cr>", desc = "Diagnostics" },
        },
        config = function()
            local t = require("telescope")
            t.setup({
                defaults = {
                    prompt_prefix = "   ",
                    selection_caret = " ",
                    file_ignore_patterns = { "%.git/", "node_modules/", "__pycache__/" },
                },
            })
            pcall(t.load_extension, "fzf")
        end,
    },
    {
        "lewis6991/gitsigns.nvim",
        event = { "BufReadPre", "BufNewFile" },
        opts = {},
    },
    {
        "windwp/nvim-autopairs",
        event = "InsertEnter",
        opts = {},
    },
    {
        "akinsho/toggleterm.nvim",
        version = "*",
        keys = { { "<C-\\>", desc = "Terminal" } },
        opts = {
            open_mapping = [[<C-\>]],
            direction = "float",
            float_opts = { border = "curved" },
        },
    },
}
