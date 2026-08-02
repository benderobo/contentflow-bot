# Phase 3.2 — ELK Stack Deployment
**Scheduled:** 2026-08-08 to 2026-08-15  
**Owner:** benderobo  
**No blockers:** Can proceed independent of Phase 3.1

---

## PHASE 3.2: ELK STACK ARCHITECTURE

### Components
- **Elasticsearch 8.x:** Log storage + search (9200)
- **Kibana 8.x:** Dashboard + visualization (5601)
- **Logstash 8.x:** Log pipeline + ingestion (5000)

### Log Sources
```
nginx access logs       → /var/log/nginx/access.log
ModSecurity audit log   → /var/log/modsecurity/audit.log
Shell audit log         → /tmp/shell_audit.log
SystemD logs            → journalctl (optional)
Application logs        → /var/log/insite-api/ (optional)
```

### Deployment Timeline
- **Week 2 (08-08):** Docker Compose up + pipeline config
- **Week 2 (08-09):** Kibana dashboards + index patterns
- **Week 2 (08-10):** Elasticsearch backups + retention
- **Week 2 (08-11):** End-to-end testing + team briefing

---

## STEP 1: Create docker-compose.yml for ELK

```yaml
version: '3.8'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.10.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms1g -Xmx1g
      - logger.level=info
    ports:
      - "9200:9200"
    volumes:
      - es-data:/usr/share/elasticsearch/data
    healthcheck:
      test: curl -s http://localhost:9200 >/dev/null || exit 1
      interval: 10s
      timeout: 5s
      retries: 3
    networks:
      - elk

  kibana:
    image: docker.elastic.co/kibana/kibana:8.10.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
      - ELASTICSEARCH_USERNAME=elastic
      - XPACK_SECURITY_ENABLED=false
    depends_on:
      elasticsearch:
        condition: service_healthy
    networks:
      - elk

  logstash:
    image: docker.elastic.co/logstash/logstash:8.10.0
    ports:
      - "5000:5000"
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf:ro
      - /var/log/nginx:/var/log/nginx:ro
      - /var/log/modsecurity:/var/log/modsecurity:ro
      - /tmp:/tmp:ro
    environment:
      - LOG_LEVEL=info
    depends_on:
      elasticsearch:
        condition: service_healthy
    networks:
      - elk

volumes:
  es-data:
    driver: local

networks:
  elk:
    driver: bridge
```

---

## STEP 2: Create logstash.conf Pipeline

```
input {
  file {
    path => "/var/log/nginx/access.log"
    start_position => "beginning"
    tags => ["nginx", "access"]
    codec => plain
  }

  file {
    path => "/var/log/modsecurity/audit.log"
    start_position => "beginning"
    tags => ["modsecurity", "waf"]
    codec => json
  }

  file {
    path => "/tmp/shell_audit.log"
    start_position => "beginning"
    tags => ["audit", "shell"]
    codec => plain
  }
}

filter {
  if "nginx" in [tags] {
    grok {
      match => { 
        "message" => "%{COMBINEDAPACHELOG}"
      }
      remove_field => [ "message" ]
    }
    date {
      match => [ "timestamp", "dd/MMM/yyyy:HH:mm:ss Z" ]
      remove_field => [ "timestamp" ]
    }
  }

  if "modsecurity" in [tags] {
    json {
      source => "message"
      target => "modsec"
    }
  }

  if "shell" in [tags] {
    grok {
      match => { 
        "message" => "%{TIMESTAMP_ISO8601:timestamp} \| server=%{WORD:server} \| cmd=%{GREEDYDATA:command}"
      }
      remove_field => [ "message" ]
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "logs-%{+YYYY.MM.dd}"
    retry_forever => false
  }

  if "_grokparsefailure" in [tags] {
    stdout { codec => rubydebug }
  }
}
```

---

## STEP 3: Create Kibana Dashboards

### Dashboard 1: HTTP Request Overview
```json
{
  "title": "HTTP Request Volume & Errors",
  "visualizations": [
    {
      "type": "line_chart",
      "metric": "count",
      "groupBy": "timestamp",
      "description": "Total requests per minute"
    },
    {
      "type": "pie_chart",
      "metric": "count",
      "groupBy": "response",
      "description": "Response codes distribution (2xx, 4xx, 5xx)"
    },
    {
      "type": "table",
      "columns": ["timestamp", "host", "method", "uri", "response", "bytes"],
      "limit": 100,
      "description": "Last 100 requests"
    }
  ]
}
```

### Dashboard 2: ModSecurity WAF Activity
```json
{
  "title": "ModSecurity Rule Triggers",
  "visualizations": [
    {
      "type": "bar_chart",
      "metric": "count",
      "groupBy": "modsec.rule_id",
      "description": "Top triggered rules (by count)"
    },
    {
      "type": "table",
      "columns": ["timestamp", "modsec.rule_id", "modsec.message", "uri", "client_ip"],
      "description": "Recent rule triggers (last 20)"
    },
    {
      "type": "map",
      "metric": "count",
      "groupBy": "client_ip",
      "description": "Attack geographic distribution"
    }
  ]
}
```

### Dashboard 3: Shell Command Audit
```json
{
  "title": "Shell Command Execution Audit",
  "visualizations": [
    {
      "type": "table",
      "columns": ["timestamp", "server", "command"],
      "limit": 50,
      "description": "All executed commands (last 50)"
    },
    {
      "type": "bar_chart",
      "metric": "count",
      "groupBy": "server",
      "description": "Commands by server"
    }
  ]
}
```

### Dashboard 4: Performance Metrics
```json
{
  "title": "Endpoint Performance",
  "visualizations": [
    {
      "type": "line_chart",
      "metric": "avg(bytes_sent)",
      "groupBy": "timestamp",
      "description": "Average response size over time"
    },
    {
      "type": "bar_chart",
      "metric": "count",
      "groupBy": "uri",
      "top": 20,
      "description": "Top 20 endpoints by request count"
    }
  ]
}
```

### Dashboard 5: Security Threats
```json
{
  "title": "Detected Security Threats",
  "visualizations": [
    {
      "type": "line_chart",
      "metric": "count(modsec.rule_id)",
      "groupBy": "timestamp",
      "description": "WAF rule triggers per minute"
    },
    {
      "type": "table",
      "columns": ["timestamp", "client_ip", "threat_type", "uri"],
      "filter": "modsec.rule_id: *",
      "description": "Recent security threats"
    }
  ]
}
```

---

## STEP 4: Deployment Checklist (2026-08-08)

### Morning (30 min): Environment Setup
```bash
# Create ELK directory
mkdir -p /root/elk-stack
cd /root/elk-stack

# Copy docker-compose.yml (from above)
# Copy logstash.conf (from above)

# Verify disk space
df -h /
# Expected: > 20GB free for Elasticsearch data

# Verify Docker
docker --version && docker-compose --version
```

### Morning-Afternoon (30 min): Deploy Containers
```bash
# Start ELK stack
docker-compose up -d

# Wait for Elasticsearch to be healthy
sleep 10
curl http://localhost:9200/
# Expected: {"name": "...", "version": {...}}

# Verify Kibana
curl -I http://localhost:5601/
# Expected: 200 OK

# Check Logstash
docker-compose logs logstash | tail -20
# Expected: "Pipeline started successfully"
```

### Afternoon (1 hour): Configure Kibana
```bash
# Access Kibana
# Open: http://localhost:5601

# 1. Create index pattern
# Management → Index Patterns → Create
# Pattern name: logs-*
# Timestamp field: @timestamp

# 2. Discover
# Verify logs appearing (may take 1-2 min to ingest)

# 3. Create dashboards
# Use Dashboard app to create 5 dashboards above
# Or import from saved objects (if available)
```

### Late Afternoon (30 min): Configure Backups
```bash
# Create snapshot directory
mkdir -p /root/elk-backups

# Create backup script
cat > /root/elk-backup.sh << 'EOFBAK'
#!/bin/bash
# Daily backup of Elasticsearch indices
DATE=$(date +%Y%m%d)
curl -X PUT "localhost:9200/_snapshot/backup" -H 'Content-Type: application/json' -d '{
  "type": "fs",
  "settings": {
    "location": "/root/elk-backups"
  }
}' 2>/dev/null

curl -X PUT "localhost:9200/_snapshot/backup/backup-$DATE" -H 'Content-Type: application/json' -d '{
  "indices": "logs-*",
  "ignore_unavailable": true,
  "include_global_state": false
}' 2>/dev/null

echo "Backup $DATE created"
EOFBAK

chmod +x /root/elk-backup.sh

# Schedule daily backup (add to crontab)
# 0 2 * * * /root/elk-backup.sh
```

### Evening (1 hour): End-to-End Testing
```bash
# Test 1: Log ingestion
# Generate nginx request
curl https://bendernostur.duckdns.org/

# Check Kibana for new log entry (Discover tab)
# Expected: Request appears within 10 seconds

# Test 2: ModSecurity log ingestion (if Phase 3.1 complete)
# Generate SQL injection attempt
curl "https://bendernostur.duckdns.org/?id=1' OR '1'='1"

# Check Kibana for ModSecurity audit entry
# Expected: Rule trigger appears in logs

# Test 3: Dashboard functionality
# Open each dashboard
# Verify charts loading with data
# Expected: All dashboards show data

# Test 4: Search & filter
# Query: response:500
# Expected: Find 5xx errors if any

# Test 5: Performance
# Run load test
ab -n 100 http://localhost:5601/
# Expected: No errors, Kibana responsive
```

### Evening: Team Briefing
```bash
# Send summary
echo "Phase 3.2 (ELK Stack) DEPLOYED

Components:
✅ Elasticsearch: Storing logs, 9200
✅ Kibana: Dashboards, http://localhost:5601
✅ Logstash: Ingesting from nginx/modsecurity/audit

Dashboards:
1. HTTP Request Overview (volume, errors, top endpoints)
2. ModSecurity WAF Activity (rule triggers, attacks)
3. Shell Command Audit (executed commands)
4. Performance Metrics (response times, sizes)
5. Security Threats (detected attacks)

Data retention: 7 days (default, expandable)
Backups: Daily snapshot to /root/elk-backups

Next: Phase 3.3 (2026-08-15) - Rule tuning
"
```

---

## SUCCESS CRITERIA

- [ ] Elasticsearch running and healthy
- [ ] Kibana accessible at port 5601
- [ ] Logstash pipeline active
- [ ] Logs ingesting from all 3 sources
- [ ] 5 dashboards created and populated
- [ ] Search/filter working
- [ ] Backups configured
- [ ] No errors in container logs

---

## TROUBLESHOOTING

### Elasticsearch won't start
```bash
docker-compose logs elasticsearch | tail -50
# Check disk space: df -h /
# Check memory: free -h
# Expected: 1GB+ free RAM
```

### Logstash not ingesting logs
```bash
docker-compose logs logstash | grep -i error
# Check file paths in logstash.conf
# Verify file permissions: ls -la /var/log/nginx/access.log
```

### Kibana can't connect to Elasticsearch
```bash
curl http://elasticsearch:9200/ -v
# Verify network: docker network ls
# Check firewall: sudo ufw status
```

---

## RISK ASSESSMENT

- **Risk Level:** LOW (Docker-based, no production code changes)
- **Rollback:** `docker-compose down` removes all ELK
- **Data Loss:** Elasticsearch data in volume, backed up daily
- **Performance Impact:** None (ELK isolated from production)

---

**Status:** 📋 READY FOR DEPLOYMENT (2026-08-08)  
**Estimated Duration:** 3-4 hours  
**Next Phase:** 3.3 Rule Tuning (2026-08-15)

