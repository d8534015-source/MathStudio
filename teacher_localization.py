"""First-party English/Chinese teacher-facing UI strings.

Translate only first-party interface text. Callers must use content_label or an
explicit content boundary for names, messages, titles and resource labels.
"""
import json
import os
from pathlib import Path
import re

ZH = {
  'Review and acknowledge the current Terms, Privacy and Cookie policies.':'请阅读并确认当前服务条款、隐私政策及 Cookie 政策。',
  'Review the current account policies before recording authorization.':'请先审核当前账户政策，再进行录制授权。',
  'Review and explicitly approve the current recording scope.':'请审核并明确同意当前录制范围。',
  'OWNER-verified guardian authorization must cover this scope first.':'此范围必须先获得 OWNER 已核实的监护人授权。',
  'Invalid recording options.':'录制选项无效。',
  'Retained quota must be 12–1000 decimal GB.':'保留配额必须为 12–1000 十进制 GB。',
  'Quick Meetings cannot authorize absentee sharing.':'即时会议不能授权缺席学生分享。',
  'Only verified scheduled lessons support absentee sharing.':'只有已核实的排定课程支持缺席学生分享。',
  'This recording has no verified scheduled capture roster.':'此录制没有已核实的排定课程捕获名单。',
  'Teacher must explicitly verify absence.':'教师必须明确核实缺席情况。',
  'Enrollment or absence cannot be verified.':'无法核实报名或缺席情况。',
  'This account is not an authorized absent enrollee.':'此账户不是已授权的缺席报名学生。',
  'The recording authorization does not cover this sharing purpose.':'录制授权不覆盖此分享目的。',
  'Participant or guardian sharing authorization is missing, expired or withdrawn.':'参与者或监护人分享授权缺失、过期或已撤回。',
  'Only completed cloud recordings may be shared.':'仅可分享已完成的云端录制。',
  'Choose eligible absent accounts.':'请选择符合条件的缺席账户。',
  'Invalid share expiry.':'分享到期时间无效。',
  'Seekable playback is not ready. OWNER must configure its trusted FFmpeg and finish processing.':'可跳转播放尚未就绪，OWNER 须配置可信 FFmpeg 并完成处理。',
  'Sign in with the enrolled student account.':'请使用已报名的学生账户登录。',
  'Review the current policies before accessing a recording resource.':'访问录制资料前，请审核当前政策。',
  'Recording resource access is unavailable.':'录制资料访问不可用。',
  'Downloads are not permitted for this recording.':'此录制不允许下载。',
  'Recording resource is unavailable.':'录制资料不可用。',
  'Recording playback is not ready.':'录制播放尚未就绪。',
  'Selected local file does not match this authorized recording.':'所选本地文件与此已授权录制不匹配。',
  'Local recording upload is incomplete.':'本地录制尚未上传完整。',
  'Only a completed local recording can be uploaded.':'仅可上传已完成的本地录制。',
  'This recording was not authorized for cloud storage.':'此录制未获云端存储授权。',
  'Cloud upload authorization is expired, changed or withdrawn.':'云端上传授权已过期、变更或撤回。',
  'Recording retention expired.':'录制保留期限已到期。',
  'Standing authorization changed or expired.':'持续授权已变更或过期。',
  'Recording authorization withdrawn.':'录制授权已撤回。',
  'Student Remember Me cannot be used for teacher accounts.':'学生“记住我”不能用于教师账户。',
  'Private cloud transfer retry pending.':'私有云传输等待重试。',
  'Too many recording requests. Try again shortly.':'录制请求过多，请稍后重试。',

  'finalizing':'正在完成录制','indexing':'正在生成可拖动播放的视频',
  'Pen input protection failed. Interact mode restored.':'画笔输入保护失败，已恢复交互模式。',
  'Meeting-end confirmation is pending. Close locally now? The remote class may still be open.':'正在等待结束课堂的确认。现在关闭本地应用？远程课堂可能仍未关闭。',
  'Ending classroom; waiting for recording finalization and server confirmation. Close app remains available.':'正在结束课堂，等待录制完成及服务器确认。仍可关闭本地应用。',
  'Could not confirm that the remote classroom ended.':'无法确认远程课堂已结束。',
  'Could not confirm that the remote classroom ended. Close locally anyway?':'无法确认远程课堂已结束。仍要关闭本地应用吗？',
  'Could not authenticate meeting window. Check OWNER connectivity.':'无法验证会议窗口，请检查 OWNER 连接。',
  'Screen sharing request failed. Check OWNER connectivity.':'屏幕共享请求失败，请检查 OWNER 连接。',
  'Manage sharing / upload':'管理分享／上传','processing':'正在处理','failed':'失败','local':'已保存到本地',
  'Recording is disabled. OWNER must configure its local policy first.':'录制已禁用，OWNER 必须先配置本地录制政策。',
  'OWNER must confirm private R2 storage before recording.':'录制前 OWNER 必须确认 R2 存储为私有。',
  'OWNER has not enabled an approved recording policy.':'OWNER 尚未启用已批准的录制政策。',
  'Every student needs unexpired OWNER-recorded guardian authorization. Guests cannot be recorded.':'每位学生均须有 OWNER 记录的未过期监护人授权，访客不能被录制。',
  'Every connected participant must affirmatively consent.':'每位已连接的参与者都必须明确同意。',
  'Guardian authorization is missing or expired.':'监护人授权缺失或已过期。',
  'Guardian authorization expired.':'监护人授权已过期。',
  'Recording request expired.':'录制请求已过期。',
  'Recording authorization ended.':'录制授权已结束。',
  'Recording is stopping before a participant joins. Retry in a moment.':'正在停止录制以便参与者加入，请稍后重试。',
  'Recording storage quota reached.':'录制存储配额已用尽。',
  'Not enough free disk space for recording.':'磁盘可用空间不足，无法录制。',
  'Recording chunk too large.':'录制片段过大。',
  'Recording chunk is out of order.':'录制片段顺序不正确。',
  'Recording duration limit reached.':'已达到录制时长限制。',
  'Recording size limit reached.':'已达到录制文件大小限制。',
  'Not enough recording disk space.':'磁盘录制空间不足。',
  'Recording quota reached.':'已达到录制配额。',
  'Recording is not ready.':'录制尚未就绪。',
  'Recording unavailable.':'录制不可用。',
  'Recording access expired. Open playback again.':'录制访问权限已过期，请重新打开播放。',
  'Private cloud storage is unavailable.':'私有云存储不可用。',
  'Stop this recording before deleting it.':'请先停止此录制再删除。',
  'Only the recording teacher can stop it.':'仅开始录制的教师可以停止录制。',
  'A recording request is already open.':'已有待处理的录制请求。',
  'No recording request is ready.':'尚无就绪的录制请求。',
  'Annotations are not synced. Close and discard pending ink?':'批注尚未同步，是否关闭并丢弃待上传笔迹？',

  'Recording':'录制','Recording notice':'录制通知','Pause/resume':'暂停／继续','Stop recording':'停止录制','Start recording in the Video panel after consent.':'在视频面板取得同意后开始录制。','Saving annotation…':'正在保存批注…','Offline · annotation retained locally':'离线 · 批注已暂存在本地',
  'Annotation queue full. Reconnect before continuing; pending ink is retained.':'批注队列已满，请重新连接后继续；待上传笔迹已保留。',
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
    'OWNER server connection': 'OWNER 服务器连接',
    'Change OWNER server': '更改 OWNER 服务器',
    'Change OWNER server? Finish active lessons first. This signs you out of the dashboard.': '更改 OWNER 服务器吗？请先结束当前课程，此操作将退出教师端登录。',

    'Connected to OWNER HTTPS server': '已连接 OWNER HTTPS 服务器',

    'OWNER and Teacher Ready builds do not match. Ask the owner to install the matching package.': 'OWNER 与教师端版本不匹配，请联系所有者安装对应版本。',
    'Check the OWNER HTTPS address and ask the owner to keep its backend running. Teacher Ready never starts a local backend.': '请检查 OWNER HTTPS 地址，并确认所有者的服务器正在运行。教师端不会在本机启动服务器。',
    'Could not start the local teacher meeting. Check setup and diagnostics.': '无法启动本机课堂，请检查安装及诊断信息。',

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

ZH.update({'OWNER connection needs attention': 'OWNER 连接需要检查', 'OWNER redirected to another address. Enter the current OWNER HTTPS address.': 'OWNER 重定向至其他地址，请输入当前 OWNER HTTPS 地址。', 'This address did not return a MathStudio OWNER response. Check the tunnel and address.': '此地址未返回 MathStudio OWNER 响应，请检查隧道和地址。', 'The OWNER gateway requires authentication. Ask the owner to check gateway access; teacher login is separate.': 'OWNER 网关要求身份验证，请联系所有者检查网关权限。教师登录另行进行。', 'The HTTPS gateway is reachable, but OWNER is unavailable. Ask the owner to check the backend and tunnel.': 'HTTPS 网关可访问，但 OWNER 不可用，请联系所有者检查后端和隧道。', 'The OWNER address returned an HTTP error. Check the current server address.': 'OWNER 地址返回 HTTP 错误，请检查当前服务器地址。', 'The OWNER TLS certificate could not be verified. Ask the owner to repair HTTPS; do not disable certificate checks.': '无法验证 OWNER TLS 证书，请联系所有者修复 HTTPS，请勿禁用证书检查。', 'The OWNER connection timed out. Check your Internet connection, then retry or update the tunnel address.': 'OWNER 连接超时，请检查网络后重试或更新隧道地址。', 'The OWNER address could not be reached. Check Internet access and the current tunnel address, then retry.': '无法访问 OWNER 地址，请检查网络和当前隧道地址后重试。', 'Enter the OWNER HTTPS origin only, for example https://mathstudio.example.org (no password, path or query).': '仅输入 OWNER HTTPS 根地址，例如 https://mathstudio.example.org（不包含密码、路径或查询参数）。', 'Invalid OWNER server port.': 'OWNER 服务器端口无效。'})

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


# Desktop public-content manager: fixed UI strings only.
ZH.update({
  "Website Management": "网站管理",
  "Connection & studio": "连接与工作室",
  "Draft, review and publish student-facing content": "起草、审阅并发布面向学生的内容",
  "OWNER server connection and studio timezone": "OWNER 服务器连接和工作室时区",
  "Save studio timezone": "保存工作室时区",
  "Public content": "公开内容",
  "Translations": "翻译",
  "Translation settings": "翻译设置",
  "Reload": "重新加载",
  "Select public content": "选择公开内容",
  "Announcement title": "公告标题",
  "Announcement message": "公告内容",
  "Source draft (never translated automatically)": "原文草稿（不会自动翻译）",
  "Save draft": "保存草稿",
  "Publish content": "发布内容",
  "Unpublish content": "取消发布内容",
  "New announcement": "新建公告",
  "Preview English": "预览英文",
  "Preview Chinese": "预览中文",
  "Translations run on OWNER. Review before publishing.": "翻译在 OWNER 服务器上运行，发布前请审阅。",
  "Target language: zh = Simplified Chinese; en = English": "目标语言：zh = 简体中文；en = 英文",
  "Original source": "原文",
  "Translation draft": "译文草稿",
  "Previously approved text (reference only)": "之前批准的译文（仅供参考）",
  "Generate draft": "生成草稿",
  "Regenerate draft": "重新生成草稿",
  "Save translation draft": "保存译文草稿",
  "Approve & publish translation": "批准并发布译文",
  "Enable OWNER offline translation": "启用 OWNER 离线翻译",
  "Protected names and terms (one per line)": "保留原样的姓名和术语（每行一个）",
  "Save translation settings": "保存翻译设置",
  "Working…": "正在处理…",
  "Saved / loaded successfully": "已保存或加载成功",
  "Request failed. Your editor text is unchanged.": "请求失败，编辑框中的文字未变。",
  "Discard unsaved editor changes?": "放弃尚未保存的修改？",
  "Save changes or reload before changing sections.": "请先保存修改或重新加载，再切换标签页。",
  "Announcement": "公告",
  "Lesson description": "课程介绍",
  "Group description": "小班课介绍",
  "Published": "已发布",
  "Draft": "草稿",
  "Outdated — reload and save again": "内容已过期，请重新加载并再次保存",
  "Approved": "已批准",
  "Outdated": "已过期",
  "Missing": "缺少译文",
  "Save the source draft before publishing or previewing.": "发布或预览前，请先保存原文草稿。",
  "Publish content?": "发布此内容？",
  "Unpublish content?": "取消发布此内容？",
  "Replace the unsaved translation draft? Approved text stays unchanged.": "替换尚未保存的译文草稿？已批准的译文将保留。",
  "Approve and publish this reviewed translation?": "批准并发布此已审阅的译文？",
  "Content preview — unpublished": "内容预览（未发布）",
  "Preview only. Publishing requires explicit approval.": "此处仅为预览，发布需要明确批准。",
  "Ask OWNER to enable and set up offline translation.": "请联系 OWNER 管理员启用并配置离线翻译。",
  "OWNER offline translation is ready": "OWNER 离线翻译已就绪",
  "Write an announcement title and message.": "请填写公告标题和内容。",
  "Public content not found.": "未找到公开内容。",
  "Content changed. Reload before saving.": "内容已变更，请重新加载后保存。",
  "Content changed. Reload and save your draft again.": "内容已变更，请重新加载并再次保存草稿。",
  "Invalid public content.": "公开内容格式无效。",
  "Invalid public content action.": "公开内容操作无效。",
  "OWNER offline translation is unavailable.": "OWNER 离线翻译不可用。"
})

ZH.update({
  "Please log in.": "请重新登录。",
  "Admin access required.": "需要教师或管理员权限。",
  "Public translation provider is disabled.": "公开内容翻译服务尚未启用。",
  "Public translation provider failed. Original content is unchanged.": "公开内容翻译失败，原文未变。",
  "Invalid translated content.": "译文格式无效。",
  "Translation did not preserve protected content.": "译文未保留受保护的内容，请检查公式、网址和术语。",
  "Invalid translation language.": "翻译语言无效。",
  "Invalid translation settings.": "翻译设置无效。",
  "Invalid translation source or language.": "翻译来源或语言无效。",
  "Public translation source not found.": "未找到公开翻译来源。",
  "Source content changed. Refresh before translating.": "原文已变更，请重新加载后翻译。",
  "Write a public description before translating.": "请先填写公开介绍，再进行翻译。",
  "Invalid translation action.": "翻译操作无效。",
  "Translation changed. Refresh before saving.": "译文已变更，请重新加载后保存。",
  "Invalid offline translation request.": "离线翻译请求无效。",
  "Offline translation models are unavailable. Run OWNER offline translation setup.": "离线翻译模型不可用，请联系 OWNER 管理员进行设置。",
  "Offline translation is busy. Try again shortly.": "离线翻译正忙，请稍后重试。",
  "Offline translation timed out. Original content is unchanged.": "离线翻译超时，原文未变。",
  "Offline translation could not start. Run OWNER offline translation setup.": "离线翻译无法启动，请联系 OWNER 管理员进行设置。",
  "Offline translation failed. Original content is unchanged.": "离线翻译失败，原文未变。",
  "Offline translation result is too large.": "离线翻译结果过长。"
})

# PR #9 desktop pairing and optional persistent login. Authored content is untouched.
ZH.update({
    'First-Time Teacher Setup':'首次教师设置',
    'Enter the one-time authorization from the local OWNER pairing window.':'请输入本机 OWNER 配对窗口显示的一次性授权码。',
    'Teacher name':'教师姓名', 'Repeat password':'再次输入密码', 'OWNER pairing code':'OWNER 配对码',
    'Create teacher account':'创建教师账户', 'Sign in instead':'改为登录',
    'Remember me on this device':'在此设备上记住我',
    'Disable Remember Me on this device':'关闭此设备的记住我',
    'Remember Me disabled. Your next app restart will require login.':'已关闭记住我。下次启动应用时需要重新登录。',
    'Could not confirm logout. Check your connection and retry.':'无法确认退出登录。请检查网络连接后重试。',
    'Windows could not save Remember Me. Sign in without it.':'Windows 无法保存记住我。请取消此选项后登录。',
    'Remembered login expired or was revoked. Sign in again.':'已保存的登录已过期或被撤销，请重新登录。',
    'Pairing authorization is invalid or expired.':'配对授权码无效或已过期。',
    'OWNER is already initialized.':'OWNER 已完成初始化。',
    'Too many setup attempts. Wait fifteen minutes.':'设置尝试次数过多，请等待十五分钟。',
    'Re-enter your password to remember this device.':'请重新输入密码以记住此设备。',
    'Too many remembered devices. Sign out on another device first.':'已记住的设备过多，请先在另一台设备上退出登录。',
    'Use 12–256 characters.':'请使用 12 至 256 个字符。',
    'Teacher setup did not complete.':'教师设置未完成。',
    'Previous OWNER is unreachable. Local Remember Me was cleared; remote logout is unconfirmed. Reset the OWNER password to revoke old devices if needed.':'无法访问原 OWNER。已清除此设备的记住我，但尚未确认远程退出。如需撤销旧设备，请重置 OWNER 密码。',
})
