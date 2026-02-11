# STL Repair Engine Comparison Test Results

**Generated:** 2026-02-10 21:19:26
**Platform:** Windows 11
**Python:** 3.12.9
**Trimesh:** 4.11.1


## Local Engine Test

**Engine:** `local`
**Input File:** `tests/non-manifold-test.stl`
**Repair Time:** 13.528s

### Metrics Comparison

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| File Size | 2,607,484 | 1,157,484 | -1,450,000 |
| Face Count | 52,148 | 23,148 | -29,000 |
| Vertex Count | 25,458 | 11,572 | -13,886 |
| Is Watertight | [X] | [OK] | +1 |
| Is Volume | [X] | [OK] | +1 |
| Euler Number | 816 | -2 | -818 |
| Volume | N/A | 203.17 | - |
| Surface Area | 711.64 | 281.82 | -429.83 |

<details>
<summary>Raw Repair Output</summary>

**stdout:**
```
Checking file: ./non-manifold-test.stl
  Repairing...
Saved repaired STL (1,157,484 bytes) to ./non-manifold-test.stl

```

**stderr:**
```
(empty)
```
</details>


## Windows Engine Test

**Engine:** `windows`
**Input File:** `tests/non-manifold-test.stl`
**Repair Time:** 19.251s

### Metrics Comparison

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| File Size | 2,607,484 | 1,157,484 | -1,450,000 |
| Face Count | 52,148 | 23,148 | -29,000 |
| Vertex Count | 25,458 | 11,572 | -13,886 |
| Is Watertight | [X] | [OK] | +1 |
| Is Volume | [X] | [OK] | +1 |
| Euler Number | 816 | -2 | -818 |
| Volume | N/A | 203.17 | - |
| Surface Area | 711.64 | 281.82 | -429.83 |

<details>
<summary>Raw Repair Output</summary>

**stdout:**
```
Checking file: ./non-manifold-test.stl
  Repairing...
Warning: Windows RepairAsync output is not watertight after processing.
Falling back to local repair...
Saved repaired STL (1,157,484 bytes) to ./non-manifold-test.stl

```

**stderr:**
```
(empty)
```
</details>


## Side-by-Side Comparison

| Metric | Local (pymeshfix) | Windows (RepairAsync) |
|--------|-------------------|------------------------|
| File Size | 1,157,484 | 1,157,484 |
| Face Count | 23,148 | 23,148 |
| Vertex Count | 11,572 | 11,572 |
| Is Watertight | [OK] | [OK] |
| Is Volume | [OK] | [OK] |
| Euler Number | -2 | -2 |
| Volume | 203.17 | 203.17 |
| Surface Area | 281.82 | 281.82 |
| **Repair Time** | 13.528s | 19.251s |

### Face Count Analysis

- **Local engine face count:** 23,148
- **Windows engine face count:** 23,148
- **Absolute difference:** 0
- **Percentage difference:** 0.00%
- **Assessment:** [OK] PASS (< 5% difference)

### Watertight Status

- **Local engine:** [OK] Watertight
- **Windows engine:** [OK] Watertight
- **Assessment:** [OK] Both engines produced watertight meshes