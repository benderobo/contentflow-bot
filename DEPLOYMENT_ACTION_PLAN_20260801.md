# Phase 3.1 Deployment Action Plan
**Date:** 2026-08-01 (Tomorrow)  
**Window:** 02:00-03:30 UTC (90 minutes)  
**Owner:** benderobo

---

## ⚠️ CRITICAL DECISION: nginx ModSecurity Module

**Status:** nginx 1.18.0 does NOT have ModSecurity module compiled  
**Options:**
1. **Option A (Fastest):** Use Docker WAF proxy (staging only, migrate to production 08-02)
2. **Option B (Recommended):** Compile nginx with ModSecurity (requires build tools, ~45 min)
3. **Option C (Conservative):** Delay Phase 3.1 to 2026-08-02 (compile today/tonight)

**Recommendation:** Option B (compile with ModSecurity support)

---

## PHASE 3.1 DEPLOYMENT SCHEDULE (2026-08-01)

### 01:45 UTC — PRE-DEPLOYMENT CHECKS (15 min)
```bash
# Verify no active deployments
sudo systemctl status insite-api mimo-brain nginx --no-pager

# Verify backups exist
ls -lh /root/backups/nginx-config-*.tar.gz

# Test rollback (on paper only)
echo "Rollback: sudo cp /root/backups/nginx-config-TIMESTAMP.tar.gz /etc/nginx/ && systemctl reload nginx"
```

### 02:00 UTC — COMPILATION PHASE (45 min)

**Step 1: Get nginx source + dependencies (10 min)**
```bash
sudo apt-get install -y build-essential libpcre3 libpcre3-dev zlib1g zlib1g-dev libssl-dev libgd-dev libgeoip-dev wget
cd /tmp
wget http://nginx.org/download/nginx-1.18.0.tar.gz
tar xzf nginx-1.18.0.tar.gz
cd nginx-1.18.0
```

**Step 2: Get ModSecurity connector (5 min)**
```bash
cd /tmp
git clone --depth 1 https://github.com/SpiderLabs/ModSecurity-nginx.git
```

**Step 3: Configure & compile (20 min)**
```bash
cd /tmp/nginx-1.18.0
./configure \
  --with-compat \
  --add-dynamic-module=/tmp/ModSecurity-nginx \
  --prefix=/etc/nginx \
  --sbin-path=/usr/sbin/nginx \
  --modules-path=/usr/lib/nginx/modules \
  --conf-path=/etc/nginx/nginx.conf \
  --error-log-path=/var/log/nginx/error.log \
  --http-log-path=/var/log/nginx/access.log \
  --pid-path=/var/run/nginx.pid \
  --lock-path=/var/run/nginx.lock

make modules
sudo cp objs/ngx_http_modsecurity_module.so /usr/share/nginx/modules/
```

**Step 4: Enable module in nginx (5 min)**
```bash
sudo bash -c 'echo "load_module /usr/share/nginx/modules/ngx_http_modsecurity_module.so;" > /etc/nginx/modules-enabled/50-mod-modsecurity.conf'
sudo nginx -t  # MUST pass before reload
```

### 02:50 UTC — MODSECURITY ACTIVATION (15 min)

**Step 5: Enable ModSecurity rules in nginx**
```bash
# Point production config to ModSecurity snippet
sudo sed -i '/listen 8443/a \    include /etc/nginx/snippets/modsecurity.conf;' \
           /etc/nginx/sites-available/bendernostur.duckdns.org
```

**Step 6: Test & reload**
```bash
sudo nginx -t
sudo systemctl reload nginx

# Verify HSTS header
curl -I https://bendernostur.duckdns.org:8443 | grep Strict-Transport
# Expected: Strict-Transport-Security: max-age=31536000
```

### 03:05 UTC — MONITORING PHASE (25 min)

**Step 7: Monitor for errors (every 2 minutes)**
```bash
# Check nginx errors
sudo tail -50 /var/log/nginx/error.log | grep -i modsecurity

# Check ModSecurity audit log
tail -20 /var/log/modsecurity/audit.log | grep -o '"id":[0-9]*' | sort | uniq

# Check request latency (should be < 5% increase)
ab -n 100 https://bendernostur.duckdns.org:8443/
```

**Step 8: Test detection mode (NOT blocking)**
```bash
# Legitimate request - should PASS
curl https://bendernostur.duckdns.org/api/orders

# SQL injection attempt - should be DETECTED, not blocked
curl "https://bendernostur.duckdns.org/?id=1' OR '1'='1"
# Expected: Request succeeds, audit.log shows rule trigger

# XSS attempt - should be DETECTED, not blocked
curl "https://bendernostur.duckdns.org/?msg=<script>alert('xss')</script>"
# Expected: Request succeeds, audit.log shows rule trigger
```

### 03:30 UTC — COMPLETION

**Step 9: Final verification**
```bash
# All services running?
sudo systemctl is-active nginx insite-api mimo-brain
# Expected: active active active

# No errors in logs?
sudo journalctl -u nginx -n 20 --no-pager
# Expected: No CRITICAL or ALERT messages

# ModSecurity in detection mode?
grep "SecRuleEngine" /etc/nginx/modsec/modsecurity.conf
# Expected: SecRuleEngine DetectionOnly

# Performance acceptable?
echo "Deployment complete with detection mode active"
```

---

## ROLLBACK PROCEDURE (If needed)

### If nginx fails to start:
```bash
sudo systemctl stop nginx
sudo rm /usr/share/nginx/modules/ngx_http_modsecurity_module.so
sudo rm /etc/nginx/modules-enabled/50-mod-modsecurity.conf
sudo sed -i '/include \/etc\/nginx\/snippets\/modsecurity.conf;/d' /etc/nginx/sites-available/bendernostur.duckdns.org
sudo systemctl start nginx
echo "Rollback complete"
```

### If performance degrades > 5%:
```bash
sudo sed -i 's/SecRuleEngine DetectionOnly/SecRuleEngine Off/' /etc/nginx/modsec/modsecurity.conf
sudo systemctl reload nginx
echo "ModSecurity disabled (but still loaded)"
```

---

## SUCCESS CRITERIA

- [ ] nginx reloads without errors
- [ ] ModSecurity module loaded successfully
- [ ] HSTS header present in responses
- [ ] 99%+ of requests processed without error
- [ ] Detection mode capturing SQL injection/XSS attempts
- [ ] Response time impact < 5%
- [ ] No 5xx errors in error.log

---

## TEAM NOTIFICATION

**Post-deployment message:**
```
✅ Phase 3.1 COMPLETE (2026-08-01)

ModSecurity WAF now active in DETECTION MODE.

What changed:
- nginx now has ModSecurity module loaded
- All HTTP requests scanned against OWASP CRS rules
- Malicious attempts logged but NOT blocked (detection only)
- Response time impact: < 2%

Next phase (2026-08-08):
- Week 2: Deploy ELK stack for log aggregation
- Week 3: Tune false positives
- Week 4: Enable blocking mode (enforcement)

Questions? See /root/INCIDENT_RESPONSE_PLAN.md
```

---

**Status:** Ready to execute  
**Risk Level:** Medium (nginx recompilation required)  
**Estimated Success Rate:** 95% (compilation usually smooth)
