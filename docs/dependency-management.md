# Dependency Management Guide

## Core Principle: Always Upgrade Package Versions

When encountering dependency conflicts or compatibility issues, the solution is to **upgrade package versions**, never downgrade.

## Why Upgrade?

1. **Security**: Newer versions contain security fixes
2. **Compatibility**: Newer packages are designed to work together
3. **Features**: Access to latest features and improvements
4. **Long-term Maintenance**: Easier to maintain current dependencies than legacy ones

## Resolving Dependency Conflicts

### Step 1: Identify the Conflict

When you see an error like:
```
The conflict is caused by:
    package-a 1.0.0 depends on core-lib>=2.0.0
    package-b 2.0.0 depends on core-lib>=3.0.0
```

### Step 2: Upgrade to Meet All Requirements

**CORRECT** ✅:
- Upgrade `core-lib` to `3.0.0` or higher to satisfy both dependencies
- If needed, upgrade `package-a` to a version compatible with `core-lib>=3.0.0`

**INCORRECT** ❌:
- Downgrading `package-b` to work with older `core-lib`
- Pinning to exact versions without considering dependencies

### Step 3: Update All Related Packages

When upgrading one package, check if related packages also need upgrades:
```
# Example: Upgrading llama-index ecosystem
llama-index-core==0.12.5 → 0.12.36
llama-index-llms-anthropic==0.6.0 → 0.7.0
anthropic==0.39.0 → >=0.50.0
```

## Common Patterns

### Pattern 1: Version Mismatch
```
Error: llama-index-llms-anthropic 0.7.0 depends on llama-index-core>=0.12.36
Current: llama-index-core==0.12.5
```

**Solution**: Upgrade `llama-index-core` to `0.12.36` or higher

### Pattern 2: Missing Module
```
ModuleNotFoundError: No module named 'anthropic.types.beta.prompt_caching'
```

**Root Cause**: Package version too old or incompatible

**Solution**: Identify which package provides the module and upgrade it

### Pattern 3: Cascading Dependencies
When one upgrade requires others:

1. Start with the core/base package
2. Upgrade dependent packages in order
3. Make all related changes together before rebuilding (builds are slow)

## Best Practices

1. **Read Error Messages Carefully**: They usually tell you exactly what version is needed
2. **Check Compatibility**: Look at package documentation for version compatibility matrices
3. **Batch Changes**: Since builds take time, make all necessary dependency updates together
4. **Incremental Upgrades**: When making large version jumps, upgrade in smaller steps if issues arise
5. **Document Changes**: Keep track of what was upgraded and why

## Example Resolution

**Problem**: Backend fails to start with import error

**Investigation**:
- Error shows missing module in newer API
- Check which package version introduced this module
- Identify all packages that depend on it

**Resolution**:
```diff
# Before
-llama-index-core==0.12.5
-llama-index-llms-anthropic==0.6.0
-anthropic==0.39.0

# After
+llama-index-core==0.12.36
+llama-index-llms-anthropic==0.7.0
+anthropic>=0.50.0
```

## Emergency Rollback

Only in extreme cases where upgrade path is blocked:
1. Document the specific blocking issue
2. Create a plan for eventual upgrade
3. Set a reminder to revisit

But this should be a last resort, not the default approach.

## Summary

- ✅ **Always go up in versions**
- ✅ **Upgrade dependencies together**
- ✅ **Batch related changes before rebuilding**
- ✅ **Read error messages for version requirements**
- ❌ **Never downgrade to "fix" compatibility**
- ❌ **Avoid pinning to exact old versions**
