// Pure figure logic of papers/lifted-surgery.html (papers/js/lifted-surgery-logic.js). The real-data tests read
// papers/data/lifted-surgery.json and hold it to the columns of the paper's Tables 1 and 2 (arXiv:2610.05307).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { parseGroup, families, ratio, codeGain, bestOrbits, visible, sortCodes, slots, move } from '../../../../papers/js/lifted-surgery-logic.js';

const DATA = JSON.parse(readFileSync(new URL('../../../../papers/data/lifted-surgery.json', import.meta.url), 'utf8'));
const T2 = DATA.certified.filter(c => c.table === 2);

test('parseGroup names the families and writes the groups as the paper does', () => {
  assert.deepEqual(parseGroup('S3xZ6'), { family: 'S3', label: 'S3 × Z6', html: 'S<sub>3</sub>&nbsp;&times;&nbsp;Z<sub>6</sub>' });
  assert.deepEqual(parseGroup('Z9x|8Z12'), { family: 'Z9⋊Z12', label: 'Z9 ⋊ Z12 (r = 8)', html: 'Z<sub>9</sub>&nbsp;&#8906;<sub>8</sub>&nbsp;Z<sub>12</sub>' });
  assert.deepEqual(parseGroup('SL23xZ5'), { family: 'SL(2,3)', label: 'SL(2,3) × Z5', html: 'SL(2,3)&nbsp;&times;&nbsp;Z<sub>5</sub>' });
  assert.equal(parseGroup('A4xZ12').family, 'A4');
  assert.equal(parseGroup('D4xZ7').html, 'D<sub>4</sub>&nbsp;&times;&nbsp;Z<sub>7</sub>');
  assert.throws(() => parseGroup('Q8'));
});

test('families come in a fixed order and only when present', () => {
  assert.deepEqual(families([{ group: 'S4xZ5' }, { group: 'S3xZ7' }, { group: 'S3xZ9' }]), ['S3', 'S4']);
  assert.deepEqual(families(DATA.certified), ['S3', 'D4', 'D5', 'Z9⋊Z12', 'A4', 'S4', 'SL(2,3)']);
});

test('ratio reduces mu / base', () => {
  assert.equal(ratio(12, 4), '3');
  assert.equal(ratio(10, 3), '10/3');
  assert.equal(ratio(9, 3), '3');
  assert.equal(ratio(6, 4), '3/2');
  assert.equal(ratio(8, 4), '2');
});

test('codeGain and bestOrbits on toy orbits', () => {
  const o = [{ mu: 12, base: 4, gamma: 3 }, { mu: 6, base: 6, gamma: 1 }, { mu: 12, base: 4, gamma: 3 }];
  assert.deepEqual(codeGain(o), { mu: 12, base: 6, text: '2' });
  assert.deepEqual(bestOrbits(o), { best: 2, examined: 3 });
});

// The gamma_code and orbits columns of Table 2, keyed by group and [[n,k,d]] (rows with equal keys agree).
const TABLE2 = {
  'S4xZ7 336,26,12': ['3', '2 of 5'], 'S4xZ7 336,24,12': ['3', '2 of 3'], 'S4xZ7 336,24,10': ['3', '2 of 2'],
  'S4xZ6 288,24,10': ['3', '1 of 1'], 'S4xZ5 240,24,10': ['2', '2 of 16'], 'S4xZ5 240,18,10': ['2', '2 of 13'],
  'SL23xZ5 240,18,10': ['3', '2 of 5'], 'S4xZ5 240,24,8': ['3', '1 of 1'], 'S4xZ5 240,24,6': ['3', '1 of 1'],
  'SL23xZ6 288,20,6': ['10/3', '1 of 1'], 'A4xZ12 288,28,6': ['2', '1 of 2'], 'A4xZ9 216,24,6': ['3', '1 of 1'],
};
test('on the real data, codeGain and bestOrbits give Table 2 of the paper', () => {
  for (const c of T2) {
    const key = `${c.group} ${c.n},${c.k},${c.d}`, b = bestOrbits(c.orbits.list);
    const want = TABLE2[key] ?? (key === 'S4xZ3 144,24,6' ? ['3', null] : undefined);
    assert.ok(want, key);
    assert.equal(codeGain(c.orbits.list).text, want[0], key);
    if (want[1]) assert.equal(`${b.best} of ${b.examined}`, want[1], key);
  }
  // the three [[144,24,6]] codes: 1 of 4, 2 of 5, 2 of 5
  assert.deepEqual(T2.filter(c => c.n === 144).map(c => bestOrbits(c.orbits.list)).map(b => `${b.best} of ${b.examined}`).sort(), ['1 of 4', '2 of 5', '2 of 5']);
  assert.equal(T2.filter(c => Number(codeGain(c.orbits.list).text.split('/')[0]) / (Number(codeGain(c.orbits.list).text.split('/')[1]) || 1) >= 3).length, 13);
});

test('visible filters by gain and by family', () => {
  const cs = [{ table: 1, group: 'S3xZ7' }, { table: 2, group: 'S4xZ5' }, { table: 2, group: 'S3xZ9' }];
  assert.equal(visible(cs, { gain: 'all', family: 'all' }).length, 3);
  assert.deepEqual(visible(cs, { gain: '2', family: 'all' }), [cs[0]]);
  assert.deepEqual(visible(cs, { gain: '3', family: 'S3' }), [cs[2]]);
  assert.equal(visible(DATA.certified, { gain: '3', family: 'all' }).length, 16);
  assert.equal(visible(DATA.certified, { gain: 'all', family: 'Z9⋊Z12' }).length, 4);
});

test('sortCodes orders by n, then d, then table, then id', () => {
  const cs = [{ id: 'b', n: 80, d: 10, table: 1 }, { id: 'a', n: 60, d: 6, table: 1 }, { id: 'c', n: 80, d: 6, table: 2 }, { id: 'd', n: 80, d: 6, table: 1 }];
  assert.deepEqual(sortCodes(cs).map(c => c.id), ['a', 'd', 'c', 'b']);
  assert.notEqual(sortCodes(cs), cs);
});

test('slots spread codes that share n and d symmetrically about their point', () => {
  const cs = [{ id: 'a', n: 216, d: 6 }, { id: 'b', n: 216, d: 6 }, { id: 'c', n: 216, d: 6 }, { id: 'e', n: 216, d: 9 }];
  assert.deepEqual(Object.fromEntries(slots(cs)), { a: -1, b: 0, c: 1, e: 0 });
  assert.deepEqual(Object.fromEntries(slots(cs.slice(0, 2))), { a: -0.5, b: 0.5 });
  const all = slots(DATA.certified);
  assert.equal(all.size, 27);
  assert.equal(Math.max(...all.values()), 1);
});

test('move steps through a list with arrow keys, Home and End, and ignores other keys', () => {
  assert.equal(move(0, 'ArrowRight', 5), 1);
  assert.equal(move(0, 'ArrowDown', 5), 1);
  assert.equal(move(4, 'ArrowRight', 5), 4);
  assert.equal(move(0, 'ArrowLeft', 5), 0);
  assert.equal(move(3, 'ArrowUp', 5), 2);
  assert.equal(move(2, 'Home', 5), 0);
  assert.equal(move(2, 'End', 5), 4);
  assert.equal(move(2, 'a', 5), null);
});
