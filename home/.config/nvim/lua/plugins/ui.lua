return {
    {
        "catppuccin/nvim",
        name = "catppuccin",
        lazy = false,
        priority = 1000,
        opts = {
            flavour = "mocha",
            integrations = {
                blink_cmp = true,
                bufferline = true,
                gitsigns = true,
                mason = true,
                nvimtree = true,
                telescope = { enabled = true },
                treesitter = true,
                which_key = true,
                indent_blankline = { enabled = true },
                native_lsp = {
                    enabled = true,
                    virtual_text = {
                        errors = { "italic" },
                        warnings = { "italic" },
                        information = { "italic" },
                        hints = { "italic" },
                    },
                    underlines = {
                        errors = { "underline" },
                        warnings = { "underline" },
                        information = { "underline" },
                        hints = { "underline" },
                    },
                },
            },
        },
        config = function(_, opts)
            require("catppuccin").setup(opts)
            vim.cmd.colorscheme("catppuccin")
        end,
    },
    {
        "akinsho/bufferline.nvim",
        version = "*",
        event = "VeryLazy",
        dependencies = "nvim-tree/nvim-web-devicons",
        opts = {
            options = {
                diagnostics = "nvim_lsp",
                separator_style = "thin",
                show_buffer_close_icons = true,
                always_show_bufferline = true,
                offsets = {
                    { filetype = "NvimTree", text = "", padding = 1 },
                },
            },
        },
    },
    {
        "lukas-reineke/indent-blankline.nvim",
        main = "ibl",
        event = { "BufReadPost", "BufNewFile" },
        opts = { indent = { char = "│" }, scope = { enabled = true } },
    },
    {
        "folke/which-key.nvim",
        event = "VeryLazy",
        opts = { preset = "modern" },
    },
    {
        "catgoose/nvim-colorizer.lua",
        event = { "BufReadPost", "BufNewFile" },
        opts = { user_default_options = { names = false } },
    },
}
