"""First-party English/Chinese teacher-facing UI strings.

Translate only first-party interface text. Callers must use content_label or an
explicit content boundary for names, messages, titles and resource labels.
"""
import json
import os
from pathlib import Path
import re

ZH = {
  'Dashboard':'主页', 'Schedule':'课表', 'Bookings':'预约', 'Students':'学生', 'Groups':'群组', 'Groups & chats':'群组与聊天',
  'Files & codes':'文件与分享码', 'Files & access codes':'文件与分享码', 'Meetings':'在线课堂', 'Student site':'学生网站',
  'WORKSPACE':'工作台','Teacher workspace':'教师工作台','Administrator':'管理员','Teacher':'教师','Student':'学生',
  'admin':'管理员','student':'学生','guest':'访客','group':'群组','instant':'即时课堂',
  'Refresh data':'刷新数据','Sign out':'退出登录','Refresh':'刷新','New meeting':'新建课堂',
  'Quick actions':'快捷操作','Upcoming classes':'即将进行的课程','Confirmed classes remain here until you end or cancel them.':'已确认课程会保留在这里，直到教师结束或取消。',
  'No confirmed classes yet':'暂无已确认课程','Confirmed bookings and group lessons will appear here.':'已确认的一对一预约和小班课将显示在这里。',
  'Open schedule':'查看课表','Review requests':'查看预约申请','Start a meeting':'开始课堂',
  'STUDENT WEBSITE':'学生网站','Share the student portal':'分享学生入口','Students use this site for booking, resources, messages, and joining lessons.':'学生可以在这里预约课程、查看资料、发送消息并加入课堂。',
  'Copy student link':'复制学生网站链接','Refresh website link':'刷新网站链接','Student link copied':'学生网站链接已复制','Website link refreshed':'网站链接已更新',
  'STUDENTS':'学生','PENDING':'待确认','CLASSES':'课程','GROUPS':'群组','Pending':'待确认','Classes':'课程',
  'registered':'已注册','need a response':'需要处理','confirmed':'已确认','active chats':'活跃聊天',
  'Today’s classes, requests, and student website status':'今天的课程、预约和学生网站状态',
  'Set availability, post group lessons, and review the week':'设置可预约时间、发布小班课并查看本周课表',
  'Confirm requests and manage scheduled classes':'确认预约并管理已安排课程',
  'Accounts, roles, and group membership':'账号、权限和群组成员',
  'Persistent class conversations and lesson messages':'长期群聊与课程消息',
  'Upload resources and create student download codes':'上传资料并创建学生下载码',
  'Start the native teacher classroom and annotation tools':'启动教师课堂与标注工具',
  'Public website details and announcements':'学生网站信息与公告',
  'Teaching schedule':'教学课表','The calendar always uses the available window width.':'课表会自动适应窗口宽度。',
  'Weekly calendar':'每周课表','Add availability':'添加可预约时间','Post group lesson':'发布小班课','← Previous':'← 上一周','Next →':'下一周 →',
  'TIME':'时间','Available':'可预约','No student yet':'暂无学生','No students booked yet':'暂无学生预约',
  'Add private availability':'添加一对一可预约时间','Students can fit a 60/90-minute lesson inside this open block.':'学生可在此空闲时段内预约 60 或 90 分钟的课程。',
  'Repeat weeks':'重复周数','Until date':'截止日期','Availability added.':'已添加可预约时间。','Add to schedule':'加入课表',
  'Post a group lesson':'发布小班课','Students reserve seats; everyone is added to the lesson group chat.':'学生预订席位后，会自动加入课程群聊。',
  'Class name':'课程名称','Lesson type':'课程类型','Seats':'人数上限','Date':'日期','Time':'时间','Price label':'价格说明','Description':'描述',
  'Small-group lesson':'小班课','Price TBD':'价格待定',
  'Pending requests':'待确认预约','Needs your review':'需要处理','Confirmed classes':'已确认课程','Ready to teach':'可开始上课',
  'Pending private requests':'待确认的一对一预约','Confirmed classes to handle':'待处理的已确认课程',
  'No pending requests':'暂无待确认预约','New private booking requests will appear here.':'新的预约申请会显示在这里。',
  'Select a request, then choose an action below.':'请选择一项预约，再选择下方操作。',
  'Select a class to launch the teacher meeting, finish it, or cancel it.':'选择课程后，可开始课堂、结束课程或取消课程。',
  'Confirm':'确认','Confirm weekly…':'按周重复确认…','Decline':'拒绝','Start teacher meeting':'开始教师课堂','End class':'结束课程','Cancel class':'取消课程',
  'Student':'学生','Lesson':'课程','Date':'日期','Length':'时长','Class':'课程','Booked by':'预约学生','Scheduled':'时间','Type':'类型','Meeting':'课堂',
  'Open':'已开启','Closed':'未开启','Ready':'就绪','LIVE':'进行中','Late — ready to start':'已过开始时间，可立即开始',
  'Private':'一对一','Group':'小班课','Instant':'即时课堂','No students yet':'暂无学生','Join by code':'通过课堂码加入',
  'Select a pending request first.':'请先选择一项待确认预约。','Select a class first.':'请先选择一门课程。',
  'Decline this booking request?':'确定拒绝此预约申请吗？','Cancel this class?':'确定取消这门课程吗？',
  'Weekly confirmation':'每周重复确认','How many weeks total?':'总共重复多少周？',
  'Registered accounts':'注册账户','Select several students to create a persistent group chat.':'选择多位学生创建长期群聊。',
  'Name':'姓名','Username':'用户名','Role':'身份','Make admin':'设为管理员','Make student':'设为学生',
  'Create group chat from selection':'用所选学生创建群聊','Select at least one student.':'请至少选择一名学生。',
  'Create group chat':'创建群聊','Group name:':'群组名称：','Select exactly one account.':'请只选择一个账户。',
  'Groups':'群组','Conversation':'会话','People':'人数','GROUP CHATS':'群组聊天','LESSON CHATS':'课程聊天',
  'Delete selected custom group':'删除所选自建群组','Persistent group chat':'长期群聊','Select a group':'请选择群组',
  'Members: ':'成员：','Lesson: ':'课程：','Send':'发送','Message':'消息',
  'Select a custom group chat. Lesson chats are tied to their class and cannot be deleted here.':'请选一个自建群组。课程群聊不能在此删除。',
  'Delete this group and its chat history?':'确定删除此群组及其聊天记录吗？',
  'File library':'文件库','Access codes':'分享码','Upload files…':'上传文件…','Generate code from selected':'为所选文件生成分享码',
  'Delete selected file':'删除所选文件','Revoke':'停用','Restore':'恢复','Enable translation':'开启翻译','Disable translation':'关闭翻译',
  'Translation on':'翻译已开启','Translation off':'翻译已关闭',
  'Code':'分享码','Label':'名称','Files':'文件','File':'文件','Size':'大小','Codes':'分享码','Status':'状态','Translation':'翻译',
  'Active':'启用','Revoked':'已停用','On':'开启','Off':'关闭',
  'Upload teacher files':'上传教师文件','Select one or more files.':'请选择一个或多个文件。',
  'Generate access code':'生成分享码','Label for this file bundle:':'资料包标签：','Shared files':'共享文件',
  'Document translation':'文档翻译',
  'Enable automatic English/Chinese document translation for this share code?\n\nStudents will see a translated reading view when the file type is supported. Translation uses an online translation service.':'是否为此分享码开启中英自动文档翻译？\n\n支持的文件会提供翻译阅读视图。翻译会使用在线服务。',
  'Select one file.':'请选择一个文件。','Delete this file from storage?':'确定从文件库删除此文件吗？',
  'Start an instant meeting':'立即开始课堂','Start instant meeting':'创建即时课堂','Scheduled meetings':'已安排课堂',
  'No scheduled class is required. MathStudio creates a 10-digit code that students can use with an account or as a guest.':'无需先安排课程。MathStudio 会生成 10 位课堂码，学生可登录账号或以访客身份加入。',
  'Select a confirmed class below, or use Instant Meeting above.':'选择下方已确认课程，或使用上方即时课堂。',
  'Start selected meeting':'开始所选课堂','Copy share code':'复制课堂码','Share code':'课堂码',
  'Full classroom opened · updates automatically':'已打开完整课堂 · 自动更新',
  'Instant math meeting':'即时数学课堂','Instant meeting':'即时课堂','Meeting title:':'课堂标题：',
  'Select an instant meeting first.':'请先选择一个即时课堂。','That scheduled class does not use a share code.':'该已安排课程不使用分享码。',
  'Share code copied':'课堂码已复制','Select a confirmed class first.':'请先选择一门已确认课程。',
  'Teacher meeting started':'教师课堂已开始',
  'Student website details':'学生网站设置','Studio name':'机构名称','Headline':'网站标题','Teacher name':'教师姓名','Contact':'联系方式',
  'Introduction':'简介','About teacher':'教师介绍','Timezone':'时区',
  'Save website settings':'保存网站设置','Student website settings saved.':'学生网站设置已保存。',
  'Publish announcement':'发布公告','Announcements appear on the student home page.':'公告将显示在学生主页。',
  'Title':'标题','Message':'消息','Publish':'发布','Announcement published.':'公告发布成功。',
  'MathStudio Teacher':'MathStudio 教师端','Teacher desktop application':'教师桌面应用',
  'Student website is offline':'学生网站未启动','Retry connection':'重试连接','Close':'关闭',
  'First double-click START STUDENT WEBSITE.bat, leave that window open, then click Retry below.':'请先运行 START STUDENT WEBSITE.bat 并保持窗口打开，然后点击下方的重试。',
  'Website: port 5051  •  Teacher app: separate process':'网站端口：5051 · 教师端：独立进程',
  'The student website server is not running.':'学生网站服务器未运行。',
  'The student website server is not running on port 5051.':'学生网站服务器未在 5051 端口运行。',
  'The website server is still offline. Start START STUDENT WEBSITE.bat first.':'网站服务器仍未启动，请先运行 START STUDENT WEBSITE.bat。',
  'Welcome back':'欢迎回来','Sign in with a teacher/admin account.':'请使用教师或管理员账户登录。',
  'Password':'密码','Sign in to Teacher':'登录教师端','Sign out':'退出登录',
  'Manage lessons without opening the admin website.':'无需打开网页管理端，即可管理课程。',
  'Schedule classes, confirm bookings, message students, share files, and launch meetings from one desktop app.':'在一个教师桌面应用中安排课程、确认预约、与学生联系、共享文件并开始课堂。',
  '● Connected':'● 已连接','● Connection problem':'● 连接异常','● Reconnecting automatically…':'● 正在自动重连…',
  'Connection problem':'连接异常','Connected':'已连接','Reconnecting automatically…':'正在自动重连…',
  'Student link copied':'学生链接已复制','Website link refreshed':'网站链接已刷新',
  'Create the first teacher account':'创建第一个教师账户','This account controls the MathStudio Teacher app.':'此账户用于管理 MathStudio 教师端。',
  'Enter a name and a username using letters, numbers, and underscores.':'请输入姓名和仅包含字母、数字、下划线的用户名。',
  'Use a password with at least 12 characters.':'请使用至少 12 位的密码。','Passwords do not match.':'两次密码不一致。',
  'That username is already in use.':'此用户名已被使用。','Create teacher account':'创建教师账户',
  'Stop camera':'关闭摄像头','Start camera':'开启摄像头','Mute':'静音','Unmute':'取消静音',
  'Share screen':'共享屏幕','Stop sharing':'停止共享','Video panel':'视频面板','Close app':'关闭应用',
  'Teacher meeting':'教师课堂','Connecting to classroom…':'正在连接课堂…',
  'Students: loading…':'正在加载学生…','Students: view only':'学生：仅可观看','Students: can draw':'学生：可以标注',
  'Interact':'交互','Draw on desktop':'桌面标注','Interact with apps':'与应用交互',
  'Pen':'画笔','Line':'直线','Rectangle':'矩形','Circle':'圆形','Text':'文字','Eraser':'橡皮擦',
  'Undo':'撤销','Clear':'清空','Hide ink':'隐藏标注','Show ink':'显示标注',
  'Interact = click through to apps · Draw = annotate desktop · Esc returns to Interact':'交互模式可操作其他应用 · 绘制模式可在桌面标注 · Esc 返回交互模式',
  'Live classroom open · native desktop annotations active':'课堂已开启 · 桌面标注已启用',
  'Exit MathStudio Teacher':'退出 MathStudio 教师端',
  'Close the Teacher App? The student website will keep running separately.':'确定关闭教师端吗？学生网站会继续运行。',
  'No student yet':'暂无学生',
}

# Annotation controls, dialogs and launcher UI; placeholders preserve user content.
ZH.update({
    'Port 5051 belongs to another MathStudio build. Stop it and start the v41.6.6 website.': '端口 5051 正由其他版本的 MathStudio 使用。请停止该进程并启动 v41.6.6 网站。',
    'Saving annotation…': '正在保存标注…',
    'Clear every shared annotation for everyone?': '确定为所有人清空共享标注吗？',
    'Sharing your desktop · students see this screen and the shared annotation layer': '正在共享桌面 · 学生可以看到此屏幕及共享标注',
    'Screen sharing stopped': '屏幕共享已停止',
    'MathStudio · You are sharing this screen': 'MathStudio · 正在共享此屏幕',
    'Class ended.': '课程已结束。',
    'The classroom is now closed.': '课堂现已关闭。',
    'MathStudio annotation': 'MathStudio 标注',
    'Text or math symbols:': '文字或数学符号：',
    'Nothing from this teacher session to undo.': '本次教师会话没有可撤销的标注。',
    'Full meeting window opened · camera, microphone, participants, chat, and annotations are available there': '完整课堂窗口已打开 · 可在其中使用摄像头、麦克风、成员列表、聊天及标注',
    'End this class for the teacher and all students?': '确定为教师和所有学生结束此课程吗？',
    'Exit this meeting?\n\nClosing the Teacher Meeting window will end the classroom for students and remove it from the active class list.': '退出此课堂吗？\n\n关闭教师课堂窗口将结束学生的课堂，并将其从当前课程列表中移除。',
    'MathStudio Teacher App': 'MathStudio 教师端',
    'Desktop meeting controls & system-wide annotations': '桌面课堂控制与全屏标注',
    'How to start a class': '如何开始课程',
    '1. Double-click OPEN MATHSTUDIO TEACHER.bat.\n2. Sign in to the Windows Teacher App.\n3. Select a confirmed class and start the meeting.\n4. Keep the meeting toolbar open while teaching.': '1. 双击 OPEN MATHSTUDIO TEACHER.bat。\n2. 登录 Windows 教师端。\n3. 选择已确认的课程并开始课堂。\n4. 上课期间请保持课堂工具栏打开。',
    'Server connected ✓  ·  Start a confirmed class from the Windows Teacher App.': '服务器已连接 ✓ · 请从 Windows 教师端开始已确认的课程。',
    'If the Admin button says the app opened but no toolbar appears, leave this window open and try Start teacher app again. The live toolbar now has a normal Windows taskbar/Alt+Tab entry.': '如果管理按钮提示应用已打开但未出现工具栏，请保持此窗口打开并重试“启动教师端”。课堂工具栏可通过 Windows 任务栏或 Alt+Tab 切换。',
    'Annotation synced · student drawings appear here automatically': '标注已同步 · 学生的绘画将自动显示在此处',
    'Media command sent · allow browser permission if prompted in the video panel': '媒体指令已发送 · 如视频面板提示，请允许浏览器权限',
    'Screen sharing needs Pillow. Restart the Teacher App; its launcher will install it automatically.': '屏幕共享需要 Pillow。请重启教师端，启动器将自动安装所需依赖。',
    'This classroom has ended.': '此课堂已结束。',
    'Student annotation enabled.': '已允许学生标注。',
    'Students are view-only.': '学生仅可观看。',
    'Could not open the teacher meeting app.\n\n{0}': '无法打开教师课堂应用。\n\n{0}',
    'MathStudio could not confirm that the class ended:\n\n': 'MathStudio 无法确认课程已结束：\n\n',
    '\n\nClose the app anyway?': '\n\n仍要关闭应用吗？',
    'Teacher App instructions': '教师端使用说明',
    'Check server': '检查服务器',
    'Server not reachable · ': '无法连接服务器 · ',
    'Server: {0}': '服务器：{0}',
    'Request failed.': '请求失败。',
    'Close': '关闭',
    'Weekly confirmation': '每周课程确认',
    'How many weeks total?': '总共安排多少周？',
    'Group name:': '群组名称：',
    'Label for this file bundle:': '此资料包的名称：',
    'Meeting title:': '课堂标题：',
    'Document translation': '文档翻译',
    'Enable automatic English/Chinese document translation for this share code?\n\nStudents will see a translated reading view when the file type is supported. Translation uses an online translation service.': '为此分享码启用英中文档自动翻译吗？\n\n对于支持的文件类型，学生将看到翻译阅读视图。翻译使用在线翻译服务。',
    'Uploaded {0} file(s).': '已上传 {0} 个文件。',
    'Posted {0} group lesson(s).': '已发布 {0} 节小班课。',
    'Access code: {0}\n\nTranslation: {1}\nThe code was copied to the clipboard.': '分享码：{0}\n\n翻译：{1}\n分享码已复制到剪贴板。',
    'Your teacher meeting is opening now.\n\nShare code: {0}\n\nOnly students need this code. They can choose Join meeting and enter it signed in or as a guest.\n\nThe code was copied to your clipboard.': '正在打开教师课堂。\n\n分享码：{0}\n\n只有学生需要此代码。学生可选择“加入课堂”，登录或以访客身份输入代码。\n\n代码已复制到剪贴板。',
    '\n\nThe meeting was created, but the native meeting window did not open automatically: ': '\n\n课堂已创建，但未能自动打开原生课堂窗口：',
    'The meeting started, but the classroom window could not open automatically.\n': '课堂已开始，但未能自动打开课堂窗口。\n',
    'The classroom opened, but the native meeting window could not be launched automatically.\n': '课堂已打开，但未能自动启动原生课堂窗口。\n',
    'On': '开',
    'Off': '关',
    'Members: ': '成员：',
    'Lesson: ': '课程：',
    'Could not sync annotation: ': '无法同步标注：',
})

PATTERNS = [
 (r'^Timezone: (.+)$', lambda m:'时区：'+m[1]),
 (r'^Could not sync annotation: (.*)$', lambda m:'无法同步标注：'+m[1]),
 (r'^Could not open meeting window: (.*)$', lambda m:'无法打开课堂窗口：'+m[1]),
 (r'^Media control failed: (.*)$', lambda m:'媒体控制失败：'+m[1]),
 (r'^Screen share reconnecting… (.*)$', lambda m:'屏幕共享正在重连… '+m[1]),
 (r'^Uploading (.+)$', lambda m:'正在上传 '+m[1]),
 (r'^● Connected · auto-updated (.+)$', lambda m:'● 已连接 · 自动更新于 '+m[1]),
 (r'^● Connected · (.+)$', lambda m:'● 已连接 · '+m[1]),
 (r'^(\d+) waiting$', lambda m:m[1]+' 项待处理'),
 (r'^(\d+) active$', lambda m:m[1]+' 项正在进行'),
 (r'^(\d+) min$', lambda m:m[1]+' 分钟'),
 (r'^Members: (.+)$', lambda m:'成员：'+m[1]),
 (r'^Lesson: (.+)$', lambda m:'课程：'+m[1]),
 (r'^Booked students: (\d+) · Online now: (\d+)(.*)$', lambda m:'已预约学生：'+m[1]+' · 在线：'+m[2]+m[3]),
 (r'^Posted (\d+) group lesson\(s\)\.$', lambda m:'已发布 '+m[1]+' 节小班课。'),
 (r'^Uploaded (\d+) file\(s\)\.$', lambda m:'已上传 '+m[1]+' 个文件。'),
]

PREF_DIR = Path(os.environ.get('APPDATA') or Path.home()) / 'MathStudio'
PREF_PATH = PREF_DIR / 'teacher_ui_preferences.json'

def read_language():
    try:
        obj=json.loads(PREF_PATH.read_text(encoding='utf-8'))
        return 'zh' if obj.get('language') == 'zh' else 'en'
    except (OSError, ValueError, TypeError, AttributeError):
        return 'en'

def save_language(lang):
    try:
        PREF_DIR.mkdir(parents=True, exist_ok=True)
        PREF_PATH.write_text(json.dumps({'language':'zh' if lang=='zh' else 'en'}),encoding='utf-8')
    except OSError:
        pass

def translate(value,lang='zh'):
    if lang!='zh' or not isinstance(value,str) or not value:
        return value
    if value in ZH:
        return ZH[value]
    stripped=value.strip()
    if stripped in ZH:
        return value.replace(stripped,ZH[stripped],1)
    # Sidebar entries with glyph prefixes should not depend on exact icon spacing.
    m=re.fullmatch(r'(\s*[^A-Za-z\s]+\s+)(.+)', value)
    if m and m[2] in ZH:
        return m[1]+ZH[m[2]]
    if value.isupper() and value.title() in ZH:
        return ZH[value.title()]
    for exp,render in PATTERNS:
        m=re.fullmatch(exp,value)
        if m:return render(m)
    return value


def content_label(factory, *args, **kwargs):
    """A label displaying user/server content, excluded from UI translation."""
    widget = factory(*args, **kwargs)
    widget._mathstudio_no_translate = True
    return widget


def localize_value(widget, key, current, translate):
    """Remember canonical UI text per heading/cell across language switches."""
    cache = getattr(widget, '_mathstudio_ui_sources', None)
    if cache is None:
        cache = widget._mathstudio_ui_sources = {}
    source, previous = cache.get(key, (current, current))
    if current != previous and current != source:
        source = current
    displayed = translate(source)
    cache[key] = (source, displayed)
    return displayed
