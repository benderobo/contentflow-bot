import os, sys
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import simpleSplit

out = sys.argv[1]
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
W, H = 595.28, 841.89
c = canvas.Canvas(out, pagesize=(W, H))
c.setTitle('Technology to the Rescue - Worksheet'); c.setAuthor('')
navy = HexColor('#18364A'); teal = HexColor('#137D87'); gray = HexColor('#57636B')
panel = HexColor('#EAF2F4'); rule = HexColor('#CCD5DB'); white = HexColor('#FFFFFF')
L, R, TW = 45, 550, 505
FOOT = 50                      # lowest y content may reach
yy = 0
BL = '____________________'    # one blank length for single words

def text(s, x=L, size=10.5, color=navy, font='Helvetica', width=TW, leading=15):
    global yy
    for ln in simpleSplit(s, font, size, width):
        c.setFont(font, size); c.setFillColor(color)
        c.drawString(x, yy, ln); yy -= leading

def page(n, title, sub):
    global yy
    c.setFillColor(navy); c.rect(0, H-99, W, 99, fill=1, stroke=0)
    c.setFillColor(teal); c.rect(0, H-103, W, 4, fill=1, stroke=0)
    c.setFillColor(white); c.setFont('Helvetica-Bold', 19); c.drawString(L, H-42, 'TECHNOLOGY TO THE RESCUE')
    c.setFont('Helvetica', 11); c.drawString(L, H-65, title)
    c.setStrokeColor(rule); c.line(L, 40, R, 40)
    c.setFillColor(gray); c.setFont('Helvetica', 8)
    c.drawString(L, 27, 'Text-based worksheet | Suggested level: B1-B2'); c.drawRightString(R, 27, str(n))
    yy = H-126; text(sub, size=10, color=gray); yy -= 6

def heading(s):
    global yy
    yy -= 8
    c.setFillColor(teal); c.rect(L, yy-3, 3, 14, fill=1, stroke=0)
    text(s, x=L+10, size=12, color=teal, font='Helvetica-Bold', leading=18); yy -= 2

def bank(s):
    global yy
    h = 24
    c.setFillColor(panel); c.roundRect(L, yy-h+14, TW, h, 4, fill=1, stroke=0)
    c.setFillColor(navy); c.setFont('Helvetica-Bold', 10); c.drawString(L+10, yy-1, s)
    yy -= h + 4

def check(n):
    assert yy > FOOT, f'page {n} overflows (y={yy:.0f})'

# ---------------- page 1
page(1, 'Vocabulary: meaning and use', 'Name: ______________________   Class: ______   Date: ____________')
text('Use the article in your textbook to complete the tasks. Focus on how the words are used in the text.')
heading('1. Match the words and phrases with their meanings.')
words = ['disaster relief','assess','restore','coordinate','reliable','autonomy','obstacle','illuminate','inflatable','distribute']
defs = ['A. to organise people or activities so that they work well together','B. something that blocks movement or makes a task difficult','C. able to be filled with air','D. to examine something and make a judgement about it','E. help given to people affected by a disaster','F. to give something to several people or places','G. the ability to work independently without direct human control','H. to bring something back to its previous condition','I. able to be trusted to work well','J. to provide light for a place']
top = yy
for i, w in enumerate(words):
    col, row = divmod(i, 5)
    x = L + col*255; y = top - row*23
    c.setFont('Helvetica', 10.5); c.setFillColor(navy)
    c.drawString(x, y, f'{i+1}. {w}')
    c.setStrokeColor(navy); c.setLineWidth(0.6); c.line(x+108, y-2, x+148, y-2)
yy = top - 5*23 - 2
c.setStrokeColor(rule); c.setLineWidth(0.6); c.line(L, yy+8, R, yy+8); yy -= 8
for d in defs: text(d, leading=20)
heading('2. Choose the correct word in each sentence.')
for s in ['1. Drones can assess / distribute the damage after a storm.','2. Rescue robots need to avoid obstacles / victims while moving through rubble.','3. Emergency lights help to illuminate / coordinate dark shelters.','4. Strong Wi-Fi can restore / inflate communication after a disaster.','5. An autonomous robot needs less remote control / disaster relief.']:
    text(s, leading=27)
check(1); c.showPage()

# ---------------- page 2
page(2, 'Vocabulary: collocations and context', 'Use vocabulary from the article. You may look back at the text.')
heading('3. Complete the collocations. Use each word once.')
bank('Bank:  efforts  |  workers  |  signal  |  zone  |  powered  |  control')
for s in [f'1. a Wi-Fi {BL}', f'2. search and rescue {BL}', f'3. relief {BL}', f'4. a disaster {BL}', f'5. solar- {BL} lighting', f'6. remote {BL}']:
    text(s, leading=23)
heading('4. Complete the paragraph. Use each word once.')
bank('Bank:  assess  |  restore  |  coordinate  |  reliable  |  distribute  |  waterproof  |  autonomy  |  relief')
b = '__________'
text(f'After a severe flood, rescue teams use drones to (1) {b} the damage. A drone carrying Wi-Fi equipment can help to (2) {b} communications. This allows relief workers to (3) {b} their efforts. A (4) {b} connection also helps people contact their families. Volunteers (5) {b} emergency lights to families without electricity. These lights are (6) {b}, so water will not damage them. Engineers are developing robots with greater (7) {b} so that they need less remote control. All these technologies can support disaster (8) {b}.', leading=22)
heading('5. Complete each sentence with the correct form of the word.')
text('Change the word in brackets.', size=10, color=gray, leading=20)
for s in [f'1. A quick {BL} (assess) of the damage helped the teams decide where to go first.',
          f'2. The {BL} (restore) of electricity took three days.',
          f'3. The {BL} (distribute) of food and water started early in the morning.',
          f'4. Because the robot is {BL} (autonomy), it can work without a human operator.',
          f'5. Rescue teams depend on {BL} (rely) communication.',
          f'6. Good {BL} (coordinate) between volunteers saves time.']:
    text(s, leading=23)
check(2); c.showPage(); c.save()
