# Phase 3.1 Revised Deployment Plan
**Original Date:** 2026-08-01  
**Revised Date:** 2026-08-02  
**Reason:** Infrastructure optimization (proper compilation environment)

---

## PHASE 3.0 (PRE-COMPILATION) — 2026-08-01

### Morning: Create Docker Build Environment (1 hour)

**Goal:** Compile ModSecurity + nginx module in isolated Docker environment

```bash
cat > /tmp/Dockerfile.modsec-build << 'EOFBUILD'
FROM ubuntu:20.04

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential autoconf automake libtool \
    libcurl4-openssl-dev libxml2-dev libpcre3-dev \
    libyajl-dev pkg-config git wget curl \
    && apt-get clean

WORKDIR /build

# Clone ModSecurity
RUN git clone --depth 1 https://github.com/SpiderLabs/ModSecurity.git

# Build ModSecurity
WORKDIR /build/ModSecurity
RUN git submodule update --init --recursive && \
    ./build.sh && \
    ./configure --prefix=/usr/local/modsecurity && \
    make && \
    make install

# Save compiled artifacts
CMD ["sh", "-c", "tar czf /artifacts/modsecurity-libs.tar.gz /usr/local/modsecurity && echo 'Build complete'"]
EOFBUILD

# Build Docker image
docker build -f /tmp/Dockerfile.modsec-build -t modsec-builder:latest /tmp/

# Run build container
docker run --rm -v /root/modsec-artifacts:/artifacts modsec-builder:latest

# Verify artifacts
ls -lh /root/modsec-artifacts/modsecurity-libs.tar.gz
```

### Afternoon: Compile nginx Module (1.5 hours)

```bash
cat > /tmp/Dockerfile.nginx-build << 'EOFNGINX'
FROM ubuntu:20.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential libpcre3 libpcre3-dev zlib1g zlib1g-dev \
    libssl-dev libgd-dev libgeoip-dev wget git pkg-config

# Copy prebuilt ModSecurity libs
COPY modsecurity-libs.tar.gz /tmp/
RUN cd /tmp && tar xzf modsecurity-libs.tar.gz

# Set library paths
ENV LD_LIBRARY_PATH=/usr/local/modsecurity/lib:$LD_LIBRARY_PATH
ENV PKG_CONFIG_PATH=/usr/local/modsecurity/lib/pkgconfig:$PKG_CONFIG_PATH

WORKDIR /build

# Download nginx source + ModSecurity connector
RUN wget http://nginx.org/download/nginx-1.18.0.tar.gz && \
    tar xzf nginx-1.18.0.tar.gz && \
    git clone --depth 1 https://github.com/SpiderLabs/ModSecurity-nginx.git

# Compile module
WORKDIR /build/nginx-1.18.0
RUN ./configure \
    --with-compat \
    --add-dynamic-module=/build/ModSecurity-nginx \
    --prefix=/etc/nginx \
    --sbin-path=/usr/sbin/nginx && \
    make modules

# Extract artifact
CMD ["cp", "objs/ngx_http_modsecurity_module.so", "/artifacts/"]
EOFNGINX

# Build image
docker build -f /tmp/Dockerfile.nginx-build \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  -t nginx-modsec-builder:latest /tmp/

# Run compilation
docker run --rm -v /root/modsec-artifacts:/artifacts nginx-modsec-builder:latest

# Verify module
file /root/modsec-artifacts/ngx_http_modsecurity_module.so
# Expected: ELF 64-bit LSB shared object
```

### Evening: Test Module Locally (30 minutes)

```bash
# Copy module to test location
sudo cp /root/modsec-artifacts/ngx_http_modsecurity_module.so \
        /usr/share/nginx/modules/

# Create test nginx config
sudo bash -c 'echo "load_module /usr/share/nginx/modules/ngx_http_modsecurity_module.so;" > /etc/nginx/modules-enabled/50-mod-modsecurity.conf'

# Test load
sudo nginx -t
# Expected: test is successful

# Test actual load
sudo systemctl reload nginx
curl -I http://localhost:8080/

# If both pass: SUCCESS ✅
# If either fails: Debug and fix before 2026-08-02
```

---

## PHASE 3.1 (PRODUCTION DEPLOYMENT) — 2026-08-02

### 02:00 UTC — Pre-flight checks (10 min)

```bash
# Verify backup exists
ls -lh /root/backups/bendernostur.duckdns.org-*.bak | tail -1

# Verify module ready
file /root/modsec-artifacts/ngx_http_modsecurity_module.so
# Expected: ELF 64-bit

# Verify services
sudo systemctl is-active nginx insite-api mimo-brain
# Expected: all active
```

### 02:10 UTC — Deploy module to production (5 min)

```bash
# Stop nginx gracefully
sudo systemctl stop nginx

# Copy module
sudo cp /root/modsec-artifacts/ngx_http_modsecurity_module.so \
        /usr/share/nginx/modules/

# Enable module
sudo bash -c 'echo "load_module /usr/share/nginx/modules/ngx_http_modsecurity_module.so;" > /etc/nginx/modules-enabled/50-mod-modsecurity.conf'

# Update production config with ModSecurity rules
sudo sed -i '/listen 8443/a \    include /etc/nginx/snippets/modsecurity.conf;' \
           /etc/nginx/sites-available/bendernostur.duckdns.org

# Test config (CRITICAL STEP)
sudo nginx -t
# Expected output: test is successful
# If test fails: Rollback immediately
```

### 02:15 UTC — Start nginx with ModSecurity (5 min)

```bash
# Start nginx
sudo systemctl start nginx

# Verify module loaded
sudo nginx -V 2>&1 | grep modsecurity
# Expected: should show modsecurity

# Check logs for errors
sudo tail -20 /var/log/nginx/error.log | grep -i error
# Expected: no critical errors

# Verify HSTS header
curl -I https://bendernostur.duckdns.org:8443 | grep Strict-Transport
# Expected: header present
```

### 02:20 UTC — Test detection mode (30 min)

```bash
# 1. Legitimate request
curl https://bendernostur.duckdns.org:8443/api/orders
# Expected: 200 OK (or appropriate app response)

# 2. Check ModSecurity detection
tail -10 /var/log/modsecurity/audit.log

# 3. SQL injection attempt (should be logged, NOT blocked)
curl "https://bendernostur.duckdns.org/?id=1' OR '1'='1"
# Expected: Request succeeds, audit.log has rule trigger

# 4. XSS attempt
curl "https://bendernostur.duckdns.org/?msg=<script>alert('test')</script>"
# Expected: Request succeeds, audit.log has rule trigger

# 5. Monitor performance
ab -n 100 https://bendernostur.duckdns.org:8443/
# Expected: Response time < 5% slower than before
```

### 02:50 UTC — Final verification (10 min)

```bash
# Check all services
sudo systemctl is-active nginx insite-api mimo-brain
# Expected: all active

# Check ModSecurity in detection mode
grep "SecRuleEngine" /etc/nginx/modsec/modsecurity.conf
# Expected: SecRuleEngine DetectionOnly

# No errors?
sudo journalctl -u nginx -n 10 --no-pager | grep -i error
# Expected: empty or normal warnings only

# Success message
echo "✅ Phase 3.1 COMPLETE - ModSecurity WAF active in detection mode"
```

---

## ROLLBACK PROCEDURE (If needed)

### If nginx fails to start:
```bash
sudo systemctl stop nginx
sudo rm /etc/nginx/modules-enabled/50-mod-modsecurity.conf
sudo sed -i '/include \/etc\/nginx\/snippets\/modsecurity.conf;/d' /etc/nginx/sites-available/bendernostur.duckdns.org
sudo systemctl start nginx
echo "Rollback complete - ModSecurity disabled"
```

### If performance > 10% slower:
```bash
sudo sed -i 's/SecRuleEngine DetectionOnly/SecRuleEngine Off/' /etc/nginx/modsec/modsecurity.conf
sudo systemctl reload nginx
echo "ModSecurity rules disabled but module still loaded"
```

---

## SUCCESS CRITERIA

- [ ] Module loads without errors
- [ ] HSTS header present
- [ ] 99%+ requests pass through
- [ ] SQL injection detected (not blocked)
- [ ] XSS detected (not blocked)
- [ ] Response time < 5% slower
- [ ] audit.log has rule triggers
- [ ] No 5xx errors

---

## ADVANTAGES OF THIS APPROACH

1. ✅ **Clean compilation** - No interference with production
2. ✅ **Tested artifacts** - Module tested before deployment
3. ✅ **Faster deployment** - 45 min compilation happens before maintenance window
4. ✅ **Easier rollback** - Pre-tested rollback procedures
5. ✅ **Version control** - Save artifacts as backup
6. ✅ **Reusable** - Module can be deployed to other nginx servers

---

**Timeline:**
- 2026-08-01: Pre-compilation & testing (4 hours)
- 2026-08-02 02:00 UTC: Production deployment (1 hour)
- 2026-08-02 03:00 UTC: Phase 3.1 COMPLETE ✅

**Risk Level:** LOW (all compilation happens offline)  
**Estimated Success Rate:** 98%
