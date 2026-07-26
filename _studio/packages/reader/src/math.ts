/* Optional maths stylesheet, imported only by editions whose content contains
   science blocks or inline equations. Splitting it out of the reader core is
   what keeps a book with no equations from shipping 1.2 MB of KaTeX fonts.
   The two imports are ordered here on purpose: KaTeX first, the reader's
   overrides of it second, which is the order they had inside the core. */
import 'katex/dist/katex.min.css';
import './styles/math.css';
