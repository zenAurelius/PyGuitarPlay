import pygame

pygame.init()

disp = pygame.display.set_mode((800,600))
pygame.display.set_caption('un test')

clock = pygame.time.Clock()
ended = False

while not ended:

	for event in pygame.event.get():
		if event.type == pygame.QUIT:
			ended = True

	print(clock.get_time())

	pygame.display.update()
	clock.tick(60)

pygame.quit()
quit()

