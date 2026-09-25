import sys, time

def main():
    import solve
    lines = [l.strip() for l in open(sys.argv[1]) if l.strip() and not l.startswith('#')]
    print(f"{len(lines)} hypotheses", flush=True)
    t0 = time.time()
    for i, l in enumerate(lines, 1):
        print(f"\n[{i}/{len(lines)}] {l}", flush=True)
        solve.run_template(l)
    print(f"\nBATCH DONE in {(time.time()-t0)/60:.1f} min", flush=True)

if __name__ == "__main__":
    main()
