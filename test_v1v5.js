// V1: missing import (does not exist)
import foo from './nonexistent-file.js';

// V1: NPM import should NOT trigger (handled by bundler, skip relative check)
import React from 'react';

// V5: fetch without timeout
fetch('https://api.example.com/data')
  .then(r => r.json())
  .catch(e => console.error(e));

// V5: axios without timeout
axios.get('/api/users');

// This should NOT trigger V5: fetch with signal
const ctrl = new AbortController();
fetch('https://api.example.com/data', { signal: ctrl.signal })
  .then(r => r.json());
