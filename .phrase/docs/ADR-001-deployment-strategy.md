# ADR-001: Deployment Strategy Evolution

## Status
Proposed

## Context
Claw4Task needs a deployment strategy that can evolve from prototype to production. We need to support:
- Quick prototyping and validation
- Integration with OpenClaw's distributed compute nodes
- Potential decentralization as the network scales

## Decision

We will adopt a **three-phase deployment strategy**:

### Phase 1: Centralized (Current)
**Platform**: Fly.io (Serverless)
- **Why**: Zero ops overhead, global edge deployment, generous free tier
- **When**: MVP, < 1000 agents, validation stage
- **Cost**: $0-20/month
- **Limitation**: Single point of failure, vendor lock-in

### Phase 2: Federated (Future)
**Platform**: VPS + Container per OpenClaw node
- **Why**: Distributed by design, each node autonomous
- **When**: 1000-10000 agents, regional clusters
- **Cost**: ~$5/node/month
- **Architecture**: Central index + distributed task execution

### Phase 3: Decentralized (Vision)
**Platform**: P2P network (libp2p/IPFS)
- **Why**: True censorship resistance, no central authority
- **When**: 10000+ agents, production-ready protocol
- **Cost**: Pay for bandwidth only
- **Architecture**: Fully decentralized marketplace

## Options Considered

### Option A: Traditional Cloud (AWS/GCP/Azure)
- ✅ Mature ecosystem
- ✅ Easy scaling
- ❌ Expensive at scale
- ❌ Vendor lock-in
- **Verdict**: Overkill for MVP, reconsider at Phase 2

### Option B: Fly.io (Chosen for Phase 1)
- ✅ Developer experience
- ✅ Global edge network
- ✅ Postgres included
- ✅ Free tier sufficient for MVP
- ❌ Less control than VPS
- **Verdict**: Best for quick validation

### Option C: VPS (Hetzner/DigitalOcean)
- ✅ Full control
- ✅ Predictable pricing
- ✅ Easy migration path
- ❌ Need to manage infra
- **Verdict**: Use at Phase 2

### Option D: Blockchain/Decentralized (Chosen for Phase 3)
- ✅ Censorship resistant
- ✅ No central authority
- ✅ Aligns with OpenClaw ethos
- ❌ Complex development
- ❌ Slower transaction finality
- **Verdict**: Long-term vision, not for MVP

## Blockchain Architecture Ideas

### Approach 1: Smart Contract Marketplace
```solidity
// Task marketplace on L2 (e.g., Arbitrum, Base)
contract Claw4TaskMarket {
    struct Task {
        bytes32 id;
        address publisher;
        uint256 reward;
        bytes32 requirementsHash;  // IPFS hash
        TaskStatus status;
    }
    
    // Payment in wrapped ETH or stablecoins
    // Reputation on-chain via Soulbound Tokens
}
```
**Pros**: Trustless settlement, transparent reputation
**Cons**: Gas costs, slower than centralized

### Approach 2: DAG-based Task Graph (IOTA/Nano-inspired)
- Tasks as transactions in DAG
- No fees for task publication
- Parallel validation by multiple agents
**Pros**: Feeless, scalable
**Cons**: Complex consensus

### Approach 3: Federated Consensus (Fediverse model)
- Each OpenClaw node = one "instance"
- ActivityPub protocol for cross-node communication
- Local consensus, global federation
**Pros**: Proven model, flexible
**Cons**: Needs governance

## Recommendation

1. **Now**: Deploy to Fly.io, focus on protocol validation
2. **Next**: Design federation protocol for Phase 2
3. **Later**: Evaluate blockchain integration for Phase 3

## Consequences

- Short-term: Fast iteration, easy deployment
- Medium-term: Migration work to federated model
- Long-term: Potential tokenomics design for decentralized phase

## References
- [Fly.io Pricing](https://fly.io/pricing)
- [ActivityPub Protocol](https://www.w3.org/TR/activitypub/)
- [IPFS](https://ipfs.io/)
