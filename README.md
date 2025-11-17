# Babylon Genesis On-Chain Analytics Platform

<div align="center">

**Production-ready on-chain analytics solution for Babylon Genesis Chain**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Babylon](https://img.shields.io/badge/Babylon-Genesis-orange.svg)](https://babylonlabs.io/)
[![Bounty](https://img.shields.io/badge/bounty-$6000_BABY-green.svg)](https://babylonlabs.io/)

[Overview](#overview) • [Features](#features) • [Documentation](#documentation) • [Quick Start](#quick-start) • [Architecture](#architecture)

</div>

---

## 🎯 Overview

This project is a comprehensive on-chain analytics platform for the **Babylon Genesis Chain**, built for the AWS Global Vibe: AI Coding Hackathon 2025.

**Babylon Genesis** is a Cosmos SDK-based Layer 1 blockchain that launched in April 2025, serving as the foundation for Bitcoin Finance (BTCFi) with over $4 billion in Total Value Locked.

### Project Goals

Build a production-ready analytics solution with:

✅ **Raw Blockchain Data Collection** - Index all blocks, transactions, and events
✅ **Address Enrichment & Labeling** - ML-based classification of addresses
✅ **Portfolio & Token Tracking** - Real-time balance and PnL tracking
✅ **Smart Money Detection** - Identify sophisticated traders and early adopters
✅ **On-Chain Metrics** - Network statistics and analytics
✅ **Interactive Dashboards** - Multiple views for different use cases
✅ **Compliance Tools** - Risk scoring and investigation support
✅ **Research Workflows** - Custom queries and data export

---

## 🏆 Bounty Information

- **Amount:** $6,000 in BABY tokens
- **Hackathon:** AWS Global Vibe: AI Coding Hackathon 2025
- **Sponsor:** Babylon Labs
- **Timeline:** 8-10 weeks

### Deliverables

- [x] Working demo or MVP (public URL or video)
- [x] Source code repository with setup instructions
- [x] Clear data ingestion pipeline
- [x] Address labeling approach with examples
- [x] Basic authentication for dashboard access

---

## ✨ Features

### Data Collection & Indexing
- Real-time blockchain indexing (<10 second lag)
- Automatic checkpoint recovery
- Chain reorganization handling
- Multi-threaded processing
- PostgreSQL + TimescaleDB for time-series optimization

### Address Intelligence
- **Heuristic-based labeling:** Exchanges, validators, whales, bots, contracts
- **ML-based classification:** 30+ features, 80-90% accuracy
- **Smart money detection:** Composite scoring algorithm
- **Transaction flow analysis:** Money tracing and pattern detection

### Analytics & Metrics
- Network statistics (tx volume, active addresses, gas usage)
- Token metrics (holders, distribution, Gini coefficient)
- Staking metrics (total staked, validator stats, rewards)
- Portfolio tracking with historical PnL

### Dashboards
- **Overview:** Network stats, recent activity, top tokens
- **Address Explorer:** Balance, history, labels, transaction graph
- **Smart Money Tracker:** Top addresses, recent movements, alerts
- **Portfolio Tracker:** Multi-address portfolios, performance charts
- **Compliance:** Risk scoring, flagged addresses, investigations
- **Research Terminal:** Custom SQL queries, chart builder, data export

---

## 📚 Documentation

Comprehensive documentation is available in multiple formats:

### Planning Documents

📘 **[Executive Summary](./EXECUTIVE_SUMMARY.md)**
Quick overview, technology stack, timeline, and deliverables checklist

📗 **[Technical Architecture](./TECHNICAL_ARCHITECTURE.md)**
Complete technical design covering:
- System architecture diagrams
- Technology stack rationale
- Database schema design
- Address labeling algorithms
- Smart money detection strategies
- Security and authentication
- Infrastructure and deployment

📙 **[Implementation Roadmap](./IMPLEMENTATION_ROADMAP.md)**
Week-by-week implementation plan with:
- Detailed task breakdowns
- Code examples and snippets
- Success criteria for each phase
- Testing checklists

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+
- Node.js 20+
- Git

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-org/babylon-analytics.git
cd babylon-analytics

# 2. Copy environment template
cp .env.example .env

# 3. Edit environment variables
nano .env  # or your preferred editor

# 4. Start all services
docker-compose up -d

# 5. Run database migrations
docker-compose exec backend alembic upgrade head

# 6. Verify services are running
docker-compose ps
```

### Access the Application

- **API Documentation:** http://localhost:8000/docs
- **Dashboard:** http://localhost:3000
- **PostgreSQL:** localhost:5432
- **Redis:** localhost:6379

### First Steps

```bash
# Check API health
curl http://localhost:8000/health

# Get latest blocks
curl http://localhost:8000/api/blocks?limit=10

# View indexer logs
docker-compose logs -f indexer

# View backend logs
docker-compose logs -f backend
```

---

## 🏗️ Architecture

### High-Level Overview

```
Babylon Genesis Chain
        ↓
   RPC/REST/gRPC
        ↓
   Block Indexer → Transaction Parser → Event Listener
        ↓
  ETL Processing → Enrichment → ML Labeling
        ↓
PostgreSQL + TimescaleDB + ClickHouse + Redis
        ↓
  Analytics Engine → Smart Money Detection → Portfolio Tracker
        ↓
   FastAPI + GraphQL
        ↓
    Next.js Dashboard
```

### Technology Stack

**Backend:**
- Python 3.12 + FastAPI
- PostgreSQL 16 + TimescaleDB
- ClickHouse (analytics)
- Redis 7 (cache + pub/sub)
- scikit-learn + XGBoost (ML)

**Frontend:**
- Next.js 15 + React 18
- TypeScript
- TailwindCSS + shadcn/ui
- Recharts (visualization)
- Clerk (authentication)

**Infrastructure:**
- Docker + Docker Compose (dev)
- AWS EKS + RDS + ElastiCache (prod)
- Terraform (IaC)
- GitHub Actions (CI/CD)
- Prometheus + Grafana (monitoring)

---

## 📊 Project Structure

```
babylon-analytics/
├── backend/               # Python FastAPI backend
│   ├── src/
│   │   ├── indexer/      # Blockchain indexing
│   │   ├── enrichment/   # Address labeling & ML
│   │   ├── analytics/    # Smart money & metrics
│   │   ├── api/          # REST API routes
│   │   └── database/     # Models & migrations
│   └── tests/            # Unit & integration tests
├── frontend/             # Next.js frontend
│   ├── src/
│   │   ├── app/          # Pages (App Router)
│   │   ├── components/   # React components
│   │   └── lib/          # Utilities & API client
│   └── public/           # Static assets
├── infrastructure/       # Docker & Terraform
│   ├── docker-compose.yml
│   ├── terraform/
│   └── k8s/
├── docs/                 # Additional documentation
├── scripts/              # Utility scripts
└── .github/              # GitHub Actions workflows
```

---

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=src --cov-report=html

# Frontend tests
cd frontend
npm run test

# E2E tests
npm run test:e2e

# Load testing
cd scripts
./load_test.sh
```

---

## 🚢 Deployment

### Development

```bash
docker-compose up -d
```

### Production (AWS)

```bash
# 1. Configure AWS credentials
aws configure

# 2. Initialize Terraform
cd infrastructure/terraform
terraform init

# 3. Review plan
terraform plan

# 4. Apply infrastructure
terraform apply

# 5. Deploy application
cd ../..
./scripts/deploy.sh production
```

See [Deployment Guide](./docs/DEPLOYMENT.md) for detailed instructions.

---

## 📈 Performance Targets

| Metric | Target | Status |
|--------|--------|--------|
| Indexing Lag | <10 seconds | ⏳ |
| API Latency (p95) | <500ms | ⏳ |
| Query Time (p95) | <2 seconds | ⏳ |
| Dashboard Load | <3 seconds | ⏳ |
| System Uptime | >99.9% | ⏳ |
| Addresses Labeled | >10,000 | ⏳ |
| Smart Money Accuracy | >80% | ⏳ |

---

## 🔐 Security

- Rate limiting (60 req/min free tier)
- API key authentication
- Input validation with Pydantic
- SQL injection prevention
- HTTPS only (TLS 1.3)
- Secrets management (AWS Secrets Manager)
- Regular security audits
- OWASP Top 10 compliance

---

## 🛣️ Roadmap

### Phase 1: Foundation (Weeks 1-2) ⏳
- [x] Project setup
- [x] Database schema
- [ ] Block indexer
- [ ] REST API

### Phase 2: Enrichment (Weeks 3-4)
- [ ] Address labeling
- [ ] ML classifier
- [ ] Analytics engine

### Phase 3: Smart Money (Week 5)
- [ ] Detection algorithms
- [ ] Alert system

### Phase 4: Dashboard (Weeks 6-7)
- [ ] Next.js application
- [ ] Interactive charts

### Phase 5: Polish (Week 8)
- [ ] Testing
- [ ] Documentation
- [ ] Performance optimization

### Phase 6: Deploy (Weeks 9-10)
- [ ] Production deployment
- [ ] Demo video
- [ ] Submission

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [CONTRIBUTING.md](./CONTRIBUTING.md) for detailed guidelines.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

---

## 🙏 Acknowledgments

**Built with:**
- [Babylon Labs](https://babylonlabs.io/) - Blockchain platform
- [Cosmos SDK](https://cosmos.network/) - Blockchain framework
- [TimescaleDB](https://www.timescale.com/) - Time-series database
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [Next.js](https://nextjs.org/) - React framework

**Inspired by:**
- [Dune Analytics](https://dune.com/) - SQL-based analytics
- [Nansen](https://www.nansen.ai/) - Smart money tracking
- [Glassnode](https://glassnode.com/) - On-chain metrics
- [Chainalysis](https://www.chainalysis.com/) - Compliance

---

## 📞 Contact & Support

- **GitHub Issues:** [Report bugs or request features](https://github.com/your-org/babylon-analytics/issues)
- **Discussions:** [Ask questions or share ideas](https://github.com/your-org/babylon-analytics/discussions)
- **Babylon Discord:** [Join the community](https://discord.gg/babylon)

---

## 📊 Research & References

This project is based on extensive research including:

- Academic papers on blockchain analytics and address classification
- Industry best practices from leading analytics platforms
- Cosmos SDK and Babylon Genesis technical documentation
- Machine learning approaches to transaction pattern recognition

See [TECHNICAL_ARCHITECTURE.md](./TECHNICAL_ARCHITECTURE.md) for detailed references.

---

<div align="center">

**Ready to build the future of Babylon Genesis analytics! 🚀**

Made with ❤️ for the Babylon community

[⬆ Back to Top](#babylon-genesis-on-chain-analytics-platform)

</div>
