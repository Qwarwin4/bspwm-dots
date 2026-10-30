return {
    {
        "mason-org/mason.nvim",
        cmd = "Mason",
        opts = { ui = { border = "rounded" } },
    },
    {
        "mason-org/mason-lspconfig.nvim",
        event = { "BufReadPre", "BufNewFile" },
        dependencies = {
            "mason-org/mason.nvim",
            "neovim/nvim-lspconfig",
            "saghen/blink.cmp",
        },
        config = function()
            vim.lsp.config("*", {
                capabilities = require("blink.cmp").get_lsp_capabilities(),
            })
            vim.lsp.config("lua_ls", {
                settings = {
                    Lua = {
                        diagnostics = { globals = { "vim" } },
                        workspace = { checkThirdParty = false },
                    },
                },
            })
            require("mason").setup()
            require("mason-lspconfig").setup({
                ensure_installed = { "lua_ls", "pyright", "clangd", "bashls" },
                automatic_enable = true,
            })
        end,
    },
    {
        "saghen/blink.cmp",
        version = "1.*",
        event = "InsertEnter",
        dependencies = "rafamadriz/friendly-snippets",
        opts = {
            keymap = { preset = "enter" },
            appearance = { nerd_font_variant = "mono" },
            completion = {
                documentation = { auto_show = true, window = { border = "rounded" } },
                menu = { border = "rounded" },
            },
            signature = { enabled = true, window = { border = "rounded" } },
            sources = { default = { "lsp", "path", "snippets", "buffer" } },
            fuzzy = { implementation = "prefer_rust_with_warning" },
        },
    },
}
