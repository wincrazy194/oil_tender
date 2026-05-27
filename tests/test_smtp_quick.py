"""
快速测试 SMTP 连接和授权码
"""
import smtplib
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, EMAIL_SENDER, EMAIL_PASSWORD

print("=" * 80)
print("SMTP 连接测试")
print("=" * 80)
print(f"SMTP 服务器: {EMAIL_SMTP_HOST}")
print(f"SMTP 端口: {EMAIL_SMTP_PORT}")
print(f"发件人邮箱: {EMAIL_SENDER}")
print(f"授权码: {'*' * (len(EMAIL_PASSWORD) - 4)}{EMAIL_PASSWORD[-4:]}")  # 只显示后4位
print("=" * 80)

try:
    print("\n正在连接 SMTP 服务器...")
    server = smtplib.SMTP_SSL(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, timeout=30)
    server.set_debuglevel(1)
    
    print("连接成功！正在登录...")
    server.login(EMAIL_SENDER, EMAIL_PASSWORD)
    
    print("✓ 登录成功！授权码有效。")
    print("\n正在发送测试邮件...")
    
    from email.mime.text import MIMEText
    msg = MIMEText("这是一封测试邮件，用于验证 SMTP 配置是否正确。", "plain", "utf-8")
    msg["Subject"] = "SMTP 配置测试"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_SENDER  # 发送给自己测试
    
    server.sendmail(EMAIL_SENDER, EMAIL_SENDER, msg.as_string())
    print("✓ 测试邮件发送成功！")
    
    server.quit()
    print("\n" + "=" * 80)
    print("所有测试通过！邮件配置正确。")
    print("=" * 80)
    
except smtplib.SMTPAuthenticationError as e:
    print(f"\n✗ 认证失败：{e}")
    print("\n可能的原因：")
    print("1. 授权码错误（注意：不是邮箱密码）")
    print("2. QQ 邮箱未开启 POP3/SMTP 服务")
    print("3. 授权码已过期")
    print("\n解决方法：")
    print("1. 登录 QQ 邮箱 → 设置 → 账户")
    print("2. 找到 'POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务'")
    print("3. 确保 'POP3/SMTP服务' 已开启")
    print("4. 重新生成授权码并更新到 .env 文件")
    sys.exit(1)
    
except smtplib.SMTPConnectError as e:
    print(f"\n✗ 连接失败：{e}")
    print("\n可能的原因：")
    print("1. 网络连接问题")
    print("2. 防火墙阻止了 465 端口")
    print("3. SMTP 服务器地址错误")
    sys.exit(1)
    
except Exception as e:
    print(f"\n✗ 发生错误：{type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
