// Перетаскивание строк в админке для смены порядка датчиков.
//
// Ручка только переставляет строку и проставляет номера в поля «порядок»,
// которые в форме уже есть. Сохраняет пользователь обычной кнопкой — своего
// эндпоинта для порядка не заводим, и правка остаётся отменяемой: ушли со
// страницы, не сохранив, — ничего не поменялось.
(() => {
  'use strict';

  const orderInput = row => row.querySelector('input[name$="-order"]');

  function init(tbody, groupOf, hintText, anchor) {
    // Ручку рисует сервер отдельной колонкой — здесь только оживляем её.
    const rows = [...tbody.rows].filter(row =>
      orderInput(row) && row.querySelector('.row-grip') && !row.classList.contains('empty-form'));
    // Меньше двух переставляемых строк — переставлять нечего, и подсказку
    // показывать не за что: в списке устройств порядка нет вовсе.
    if (rows.length < 2) return;

    const hint = document.createElement('p');
    hint.className = 'drag-hint';
    hint.textContent = hintText;
    anchor.parentNode.insertBefore(hint, anchor);

    // Django рисует флажок выбора первой колонкой, а list_display идёт
    // после него: ручку двигаем в самое начало уже здесь.
    moveHandleFirst(tbody.closest('table'));

    let drag = null;

    // Номера раздаём заново по всей таблице: порядок уникален внутри
    // устройства, поэтому нумеруем каждую группу с нуля.
    function renumber() {
      const seen = new Map();
      for (const row of tbody.rows) {
        const input = orderInput(row);
        if (!input || row.classList.contains('empty-form')) continue;
        const group = groupOf(row);
        const next = seen.get(group) || 0;
        input.value = next;
        seen.set(group, next + 1);
        // Django подсвечивает изменённые поля только по своим событиям —
        // шлём change, иначе строка не попадёт в «изменённые».
        input.dispatchEvent(new Event('change', { bubbles: true }));
      }
      markDirty();
    }

    // Копия строки едет за курсором, на её месте остаётся пустое место —
    // так же, как у карточек на странице мониторинга.
    function lift() {
      const box = drag.row.getBoundingClientRect();
      drag.grab = { x: drag.x - box.left, y: drag.y - box.top };

      const ghost = document.createElement('table');
      ghost.className = 'row-ghost';
      const body = document.createElement('tbody');
      const copy = drag.row.cloneNode(true);
      [...drag.row.cells].forEach((cell, index) => {
        copy.cells[index].style.width = cell.getBoundingClientRect().width + 'px';
      });
      body.appendChild(copy);
      ghost.appendChild(body);
      ghost.style.width = box.width + 'px';
      ghost.style.transform = `translate(${box.left}px, ${box.top}px)`;
      document.body.appendChild(ghost);

      drag.ghost = ghost;
      drag.started = true;
      drag.row.classList.add('dragging');
      document.body.classList.add('dragging-row');
    }

    // Соседи не перескакивают, а разъезжаются: снимаем их положение до и
    // после перестановки и проигрываем разницу сдвигом.
    function slide(rearrange) {
      const nodes = [...tbody.rows];
      const before = nodes.map(node => node.getBoundingClientRect().top);
      rearrange();
      nodes.forEach((node, index) => {
        if (node === drag.row) return;
        const shift = before[index] - node.getBoundingClientRect().top;
        if (!shift) return;
        node.style.transition = 'none';
        node.style.transform = `translateY(${shift}px)`;
        requestAnimationFrame(() => {
          node.style.transition = 'transform .16s ease';
          node.style.transform = '';
        });
      });
    }

    function dragOver(x, y) {
      drag.ghost.style.transform = `translate(${x - drag.grab.x}px, ${y - drag.grab.y}px)`;

      // Копия перехватывает попадание — ищем строку под ней самой.
      drag.ghost.style.visibility = 'hidden';
      const under = document.elementFromPoint(x, y);
      drag.ghost.style.visibility = '';
      const target = under && under.closest('tr');
      if (!target || target === drag.row || target.parentElement !== tbody) return;
      if (!orderInput(target) || groupOf(target) !== groupOf(drag.row)) return;   // чужое устройство
      const box = target.getBoundingClientRect();
      const before = y < box.top + box.height / 2;
      if (before ? target.previousElementSibling === drag.row
                 : target.nextElementSibling === drag.row) return;   // и так на месте
      slide(() => tbody.insertBefore(drag.row, before ? target : target.nextSibling));
    }

    function endDrag(commit) {
      if (!drag) return;
      clearTimeout(drag.timer);
      const { row, ghost, started } = drag;
      drag = null;

      row.classList.remove('dragging');
      document.body.classList.remove('dragging-row');
      for (const node of tbody.rows) node.style.transition = node.style.transform = '';

      if (ghost) {
        // Копия «приземляется» на место строки, а не пропадает рывком.
        const box = row.getBoundingClientRect();
        ghost.style.transition = 'transform .16s ease, box-shadow .16s ease';
        ghost.style.transform = `translate(${box.left}px, ${box.top}px)`;
        ghost.style.boxShadow = 'none';
        setTimeout(() => ghost.remove(), 180);
      }
      if (started && commit) renumber();
    }

    // После перестановки напоминаем, что правка ещё не сохранена.
    const markDirty = () => hint.classList.add('reordered');

    for (const row of rows) {
      const grip = row.querySelector('.row-grip');

      grip.addEventListener('pointerdown', event => {
        if (event.pointerType === 'mouse' && event.button !== 0) return;
        drag = { row, pointerId: event.pointerId, x: event.clientX, y: event.clientY, started: false, timer: 0 };
        if (event.pointerType !== 'mouse') drag.timer = setTimeout(lift, 250);
      });

      grip.addEventListener('keydown', event => {
        const up = event.key === 'ArrowUp';
        const down = event.key === 'ArrowDown';
        if (!up && !down) return;
        const sibling = up ? row.previousElementSibling : row.nextElementSibling;
        if (!sibling || !orderInput(sibling) || groupOf(sibling) !== groupOf(row)) return;
        event.preventDefault();
        if (up) tbody.insertBefore(row, sibling);
        else tbody.insertBefore(sibling, row);
        renumber();
        grip.focus();
      });
    }

    // Указатель слушаем на окне: перенос вынимает строку из таблицы, и
    // захват указателя на ручке внутри неё браузер тут же снимает.
    window.addEventListener('pointermove', event => {
      if (!drag || event.pointerId !== drag.pointerId) return;
      const far = Math.hypot(event.clientX - drag.x, event.clientY - drag.y);
      if (!drag.started) {
        // Мышь трогается с порога сдвига, палец — с удержания: иначе
        // браузер принимает начатый перенос за прокрутку.
        if (event.pointerType === 'mouse') {
          if (far <= 6) return;
          lift();
        } else if (far > 8) {
          endDrag(false);
          return;
        } else {
          return;
        }
      }
      event.preventDefault();
      dragOver(event.clientX, event.clientY);
    }, { passive: false });

    for (const type of ['pointerup', 'pointercancel']) {
      window.addEventListener(type, event => {
        if (drag && event.pointerId === drag.pointerId) endDrag(type === 'pointerup');
      });
    }
  }

  // Ручка должна стоять раньше флажка выбора, а Django рисует флажок
  // первым — переносим ячейки в разметке.
  function moveHandleFirst(table) {
    if (!table) return;
    for (const row of table.rows) {
      const handle = row.querySelector('.field-reorder_handle, th.column-reorder_handle');
      if (handle && handle !== row.cells[0]) row.insertBefore(handle, row.cells[0]);
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    // Список датчиков. Перетаскивание осмысленно только в естественном
    // порядке: при сортировке по другой колонке позиция строки не значит
    // ничего, поэтому ручек там не показываем.
    const list = document.querySelector('#result_list');
    if (list && !new URLSearchParams(location.search).has('o')) {
      const cell = row => row.querySelector('.field-device');
      init(list.tBodies[0], row => (cell(row) ? cell(row).textContent.trim() : ''),
           'Порядок меняется перетаскиванием за ручку — не забудьте нажать «Сохранить».', list);
    }

    // Датчики внутри устройства: здесь устройство одно, группировать нечего.
    for (const group of document.querySelectorAll('.inline-group')) {
      const table = group.querySelector('table');
      if (table && table.tBodies.length) {
        init(table.tBodies[0], () => '',
             'Порядок карточек меняется перетаскиванием за ручку.', table);
      }
    }
  });
})();
