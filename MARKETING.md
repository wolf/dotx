# Marketing Strategy for dotx

## Target Audience
Developers who manage dotfiles, Unix/Linux users, people who use multiple machines, people who care about their dev environment setup.

## Tier 1: Highest Impact (Do these first)

### 1. Show HN (Hacker News)
- **Why**: Single best place for dev tools. If it resonates, you'll get thousands of users overnight
- **Format**: "Show HN: dotx – A dotfile manager with database tracking"
- **Timing**: Post Tuesday-Thursday, 8-10am ET (when HN is most active)
- **Key**: The comments matter - be responsive, technical, humble about tradeoffs
- **Expected**: 50-500+ upvotes if it catches on = 10k+ visitors

### 2. r/commandline (Reddit)
- **Why**: Perfect target audience - people obsessed with CLI tools
- **Format**: Demo gif/video + explanation of the database tracking advantage
- **Tip**: Show, don't just tell. A quick demo of `dotx install` → `dotx list` → `dotx verify` is powerful
- **Expected**: 100-500 upvotes, very engaged comments

### 3. r/dotfiles (Reddit)
- **Why**: Literally people who manage dotfiles
- **Format**: "I built a dotfile manager that tracks what's installed"
- **Tip**: They'll compare to Stow/chezmoi - emphasize the database tracking differentiator
- **Expected**: 50-200 upvotes, quality feedback

### 4. awesome-dotfiles list (GitHub)
- **Why**: Passive discovery for years to come
- **Action**: Submit PR to add dotx to https://github.com/webpro/awesome-dotfiles
- **Effort**: 5 minutes, long-tail value
- **Expected**: Steady stream of GitHub stars and users over time

## Tier 2: Good Secondary Options

### 5. Lobsters
- **Why**: High-quality technical community, smaller but engaged
- **Format**: Similar to HN but more technical discussion
- **Note**: Need an invite or invitation code

### 6. r/linux and r/unixporn
- **Why**: Large communities, but less directly targeted
- **Tip**: r/unixporn cares about aesthetics - show the Rich terminal output

### 7. r/Python
- **Why**: Python developers might appreciate the clean code
- **Format**: "Show off Saturday" thread, or as a project showcase

## Lower Priority (Unless you enjoy writing/video)

- **Dev.to / Hashnode article**: "Why I built another dotfile manager" - good for SEO but takes time
- **YouTube demo**: High effort, uncertain reach unless you have an audience
- **Twitter/X**: Low impact without existing followers

## Preparation Before Posting

Make sure these are polished:
1. **README.md** - Clear, visual, shows the value quickly (✓ Done)
2. **GitHub**: Clean issues, pinned "Getting Started", topics tagged
3. **Quick wins**: Add a demo GIF to the README showing install → verify workflow
4. **PyPI page**: Make sure description renders well (✓ Done)

## Timing Strategy

1. **Week 1**: Show HN + r/commandline (same day is fine)
2. **Week 2**: Submit PR to awesome-dotfiles, post to r/dotfiles
3. **Ongoing**: Respond to issues, gather feedback, iterate

## What Makes Posts Successful

- **Show the problem**: "Ever lost track of which dotfiles package installed what?"
- **Unique angle**: Database tracking is your killer feature - emphasize it
- **Be humble**: "Another dotfile manager, but with X"
- **Demo, don't lecture**: Screenshots, GIFs, or asciinema recordings
- **Engage**: Respond to every comment in the first 3-4 hours

## Recommended Starting Point

Start with **Show HN** and **r/commandline** on the same day. If Show HN gets traction, that alone could give you hundreds of users. The Reddit post will give you quality feedback even if it doesn't blow up.

Then immediately submit to **awesome-dotfiles** for long-tail discovery.

The combination of these three will give you the best bang for buck - probably 3-4 hours of total effort for potentially thousands of users.

## Unique Selling Points to Emphasize

1. **Database tracking** - Know exactly what's installed, by which package
2. **Clean uninstall** - Unlike Stow, you can remove everything a package installed
3. **Verification** - Check if your dotfiles match what's on disk
4. **Cross-platform** - Works on macOS, Windows, Linux
5. **Simple** - No templating, no complex features - just symlinks done right
6. **gitignore-style patterns** - Familiar .dotxignore syntax

---

## Show HN Post Drafts

### Title Options

**Option 1 (Problem-focused):**
```
Show HN: dotx – Dotfile manager that remembers what it installed
```

**Option 2 (Feature-focused):**
```
Show HN: dotx – Dotfile manager with SQLite tracking and clean uninstalls
```

**Option 3 (Simple):**
```
Show HN: dotx – Link-farm dotfile manager with database tracking
```

**Option 4 (Differentiator):**
```
Show HN: dotx – Like GNU Stow but knows what it installed
```

**Recommended**: Option 1 or 4 - most accessible and hint at key differentiator.

### Description Draft 1 (Conversational)

```
I got tired of not knowing which dotfiles were installed by which package,
so I built dotx.

It's a simple dotfile manager that uses symlinks (like GNU Stow) but keeps
a SQLite database of what it installed. This means:

- `dotx list` shows all your installed packages
- `dotx uninstall bash` removes ONLY what that package installed
- `dotx verify` checks if your dotfiles match what's on disk
- `dotx sync` rebuilds the database from existing symlinks

It uses .dotxignore files (gitignore syntax) and supports file renaming
(dot-bashrc → .bashrc).

GitHub: https://github.com/wolf/dotx
PyPI: pip install dotx

I'd love feedback, especially if you currently use Stow, chezmoi, or similar tools.
```

### Description Draft 2 (Problem-focused)

```
Ever run `stow bash` and then forget what files it installed? Or uninstall
a package and wonder if you got everything?

dotx is a dotfile manager that tracks installations in SQLite:

• Know exactly what's installed: `dotx list`
• Clean uninstalls: `dotx uninstall bash` removes only that package's files
• Verify integrity: `dotx verify` checks for drift
• Recover from chaos: `dotx sync` rebuilds from existing symlinks

It's simpler than chezmoi (no templating), but more capable than Stow
(database tracking). Uses .dotxignore files and supports renaming
(dot-bashrc → .bashrc).

GitHub: https://github.com/wolf/dotx
Install: pip install dotx

Looking for feedback from anyone managing dotfiles across multiple machines.
```

### Notes for When Ready to Post

- Post Tuesday-Thursday, 8-10am ET for best visibility
- Be ready to respond to comments in first 3-4 hours
- Keep tone humble and technical
- Address comparisons to Stow/chezmoi honestly
- Mention you're open to feedback and feature requests
