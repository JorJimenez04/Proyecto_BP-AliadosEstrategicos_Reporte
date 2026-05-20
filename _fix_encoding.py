import re

file = 'app/components/crypto_ui.py'
with open(file, 'r', encoding='utf-8-sig') as f:
    lines = f.readlines()

ff_line = None
for i, l in enumerate(lines):
    if 'ff"' in l and 'defs' in l:
        ff_line = i
        break

render_finals = [i for i, l in enumerate(lines) if 'Render final' in l]
print('ff line 0-idx:', ff_line)
print('Render final lines 0-idx:', render_finals)
print('Total lines:', len(lines))

if len(render_finals) >= 2:
    first_render = render_finals[0]   # 0-indexed: start of broken st.markdown block
    second_render = render_finals[1]  # 0-indexed: start of correct st.markdown block
    new_lines = lines[:first_render] + lines[second_render:]
    with open(file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f'Deleted lines {first_render}-{second_render-1} (0-idx). New total: {len(new_lines)}')
else:
    print('Less than 2 Render final markers found — nothing to delete')
