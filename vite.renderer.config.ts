export default {
  build: {
    rollupOptions: {
      input: {
        main:    'index.html',
        overlay: 'overlay.html',
        pet:     'pet.html',
        toast:   'toast.html',
      },
    },
  },
};