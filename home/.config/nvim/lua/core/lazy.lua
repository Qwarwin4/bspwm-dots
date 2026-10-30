local path = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"

if not vim.uv.fs_stat(path) then
    local out = vim.fn.system({
        "git", "clone", "--filter=blob:none", "--branch=stable",
        "https://github.com/folke/lazy.nvim.git", path,
    })
    if vim.v.shell_error ~= 0 then
        vim.api.nvim_echo({ { "lazy.nvim clone failed:\n" .. out, "ErrorMsg" } }, true, {})
        return
    end
end
vim.opt.rtp:prepend(path)

require("lazy").setup("plugins", {
    install = { colorscheme = { "catppuccin" } },
    checker = { enabled = false },
    change_detection = { notify = false },
    ui = { border = "rounded" },
})
