// V8: useEffect with subscribe but no cleanup
useEffect(() => {
  api.subscribe('channel');
}, []);

// V8: addEventListener without removeEventListener
button.addEventListener('click', handleClick);

// V8: setInterval without clearInterval
setInterval(() => { poll(); }, 5000);

// This should NOT trigger V8: useEffect with proper cleanup
useEffect(() => {
  const sub = api.subscribe('channel');
  return () => sub.unsubscribe();
}, []);

// V9: forEach with async callback
items.forEach(async (item) => {
  await saveItem(item);
});

// This should NOT trigger V9: proper for...of with await
for (const item of items) {
  await saveItem(item);
}
