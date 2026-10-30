local o = vim.opt

o.number = true
o.relativenumber = true
o.signcolumn = "yes:1"
o.cursorline = true
o.termguicolors = true
o.mouse = "a"
o.clipboard = "unnamedplus"
o.expandtab = true
o.shiftwidth = 4
o.tabstop = 4
o.softtabstop = 4
o.smartindent = true
o.wrap = false
o.scrolloff = 8
o.sidescrolloff = 8
o.ignorecase = true
o.smartcase = true
o.splitright = true
o.splitbelow = true
o.undofile = true
o.swapfile = false
o.updatetime = 250
o.timeoutlen = 400
o.showmode = false
o.laststatus = 3
o.fillchars = { eob = " " }
o.list = true
o.listchars = { tab = "» ", trail = "·", nbsp = "␣" }

vim.diagnostic.config({
    severity_sort = true,
    underline = true,
    update_in_insert = false,
    virtual_text = { prefix = "■", spacing = 4 },
    signs = {
        text = {
            [vim.diagnostic.severity.ERROR] = "E",
            [vim.diagnostic.severity.WARN] = "W",
            [vim.diagnostic.severity.INFO] = "I",
            [vim.diagnostic.severity.HINT] = "H",
        },
    },
    float = { border = "rounded", source = true },
})

vim.api.nvim_create_autocmd("TextYankPost", {
    callback = function() vim.hl.on_yank({ timeout = 150 }) end,
})
