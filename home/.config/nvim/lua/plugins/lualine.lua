local c = {
    bg = "#202328",
    fg = "#bbc2cf",
    yellow = "#ecbe7b",
    cyan = "#008080",
    green = "#98be65",
    orange = "#ff8800",
    violet = "#a9a1e1",
    magenta = "#c678dd",
    blue = "#51afef",
    red = "#ec5f67",
}

local function wide() return vim.fn.winwidth(0) > 80 end
local function named() return vim.fn.empty(vim.fn.expand("%:t")) ~= 1 end

local modes = {
    n = c.red, i = c.green, v = c.blue, ["\22"] = c.blue, V = c.blue,
    c = c.magenta, no = c.red, s = c.orange, S = c.orange, ["\19"] = c.orange,
    ic = c.yellow, R = c.violet, Rv = c.violet, cv = c.red, ce = c.red,
    r = c.cyan, rm = c.cyan, ["r?"] = c.cyan, ["!"] = c.red, t = c.red,
}

local function lsp_name()
    local clients = vim.lsp.get_clients({ bufnr = 0 })
    if #clients == 0 then return "No Active Lsp" end
    local names = {}
    for _, cl in ipairs(clients) do table.insert(names, cl.name) end
    return table.concat(names, ", ")
end

local left = {
    { function() return "▊" end, color = { fg = c.blue }, padding = { left = 0, right = 1 } },
    { function() return "" end, color = function() return { fg = modes[vim.fn.mode()] or c.red } end, padding = { right = 1 } },
    { "filesize", cond = named },
    { "filename", cond = named, color = { fg = c.magenta, gui = "bold" } },
    { "location" },
    { "progress", color = { fg = c.fg, gui = "bold" } },
    {
        "diagnostics",
        sources = { "nvim_diagnostic" },
        symbols = { error = " ", warn = " ", info = " " },
        diagnostics_color = {
            error = { fg = c.red },
            warn = { fg = c.yellow },
            info = { fg = c.cyan },
        },
    },
    { function() return "%=" end },
    { lsp_name, icon = " LSP:", color = { fg = "#ffffff", gui = "bold" } },
}

local right = {
    { "o:encoding", fmt = string.upper, cond = wide, color = { fg = c.green, gui = "bold" } },
    { "fileformat", fmt = string.upper, icons_enabled = false, color = { fg = c.green, gui = "bold" } },
    { "branch", icon = "", color = { fg = c.violet, gui = "bold" } },
    {
        "diff",
        symbols = { added = " ", modified = "󰝤 ", removed = " " },
        diff_color = { added = { fg = c.green }, modified = { fg = c.orange }, removed = { fg = c.red } },
        cond = wide,
    },
    { function() return "▊" end, color = { fg = c.blue }, padding = { left = 1 } },
}

return {
    "nvim-lualine/lualine.nvim",
    event = "VeryLazy",
    dependencies = "nvim-tree/nvim-web-devicons",
    opts = {
        options = {
            component_separators = "",
            section_separators = "",
            globalstatus = true,
            theme = {
                normal = { c = { fg = c.fg, bg = c.bg } },
                inactive = { c = { fg = c.fg, bg = c.bg } },
            },
        },
        sections = {
            lualine_a = {}, lualine_b = {}, lualine_y = {}, lualine_z = {},
            lualine_c = left,
            lualine_x = right,
        },
        inactive_sections = {
            lualine_a = {}, lualine_b = {}, lualine_y = {}, lualine_z = {},
            lualine_c = {}, lualine_x = {},
        },
    },
}
